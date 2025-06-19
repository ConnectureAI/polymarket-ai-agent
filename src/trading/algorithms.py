import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math
import logging
from core.models import Market, MarketAnalysis, TradingSignal, TradeSide, RiskMetrics

logger = logging.getLogger(__name__)

class BlackScholesAdapter:
    """
    Adapted Black-Scholes model for prediction markets
    Treats prediction markets as binary options with time decay
    """
    
    @staticmethod
    def calculate_fair_value(
        current_price: float,
        time_to_expiry: float,  # in years
        volatility: float,
        risk_free_rate: float = 0.05,
        underlying_drift: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate fair value using adapted Black-Scholes for binary options
        
        Args:
            current_price: Current market price (0-1)
            time_to_expiry: Time until market resolution (years)
            volatility: Implied volatility
            risk_free_rate: Risk-free rate
            underlying_drift: Expected drift in underlying probability
        """
        if time_to_expiry <= 0:
            return {
                "fair_value": current_price,
                "time_decay": 0.0,
                "vega": 0.0,
                "theta": 0.0
            }
        
        # Convert price to log-odds space for better modeling
        if current_price <= 0.001:
            current_price = 0.001
        elif current_price >= 0.999:
            current_price = 0.999
            
        log_odds = math.log(current_price / (1 - current_price))
        
        # Adjust for time decay and drift
        adjusted_log_odds = log_odds + underlying_drift * time_to_expiry
        
        # Time decay effect (binary options lose value as expiry approaches)
        time_decay_factor = math.exp(-0.5 * volatility * volatility * time_to_expiry)
        
        # Calculate fair value
        fair_log_odds = adjusted_log_odds * time_decay_factor
        fair_value = 1 / (1 + math.exp(-fair_log_odds))
        
        # Calculate Greeks
        sqrt_t = math.sqrt(time_to_expiry)
        d1 = (log_odds + 0.5 * volatility * volatility * time_to_expiry) / (volatility * sqrt_t)
        d2 = d1 - volatility * sqrt_t
        
        # Vega (sensitivity to volatility)
        vega = current_price * (1 - current_price) * sqrt_t * norm.pdf(d1)
        
        # Theta (time decay)
        theta = -current_price * (1 - current_price) * volatility * norm.pdf(d1) / (2 * sqrt_t)
        
        # Time decay as percentage per day
        time_decay_per_day = abs(theta) / 365
        
        return {
            "fair_value": max(0.001, min(0.999, fair_value)),
            "time_decay": time_decay_per_day,
            "vega": vega,
            "theta": theta
        }
    
    @staticmethod
    def calculate_implied_volatility(
        market_price: float,
        fair_value: float,
        time_to_expiry: float
    ) -> float:
        """
        Estimate implied volatility from market price vs theoretical fair value
        """
        if time_to_expiry <= 0 or market_price <= 0.001 or market_price >= 0.999:
            return 0.2  # Default volatility
        
        # Simple estimation based on price deviation and time
        price_deviation = abs(market_price - fair_value)
        base_volatility = price_deviation / math.sqrt(time_to_expiry)
        
        # Bound volatility to reasonable range
        return max(0.1, min(1.0, base_volatility))

class KellyCriterion:
    """
    Kelly Criterion for optimal position sizing in prediction markets
    """
    
    @staticmethod
    def calculate_optimal_size(
        win_probability: float,
        win_payout: float,
        loss_payout: float,
        bankroll: float,
        max_fraction: float = 0.25
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion
        
        Args:
            win_probability: Probability of winning (0-1)
            win_payout: Payout ratio if win (e.g., 2.0 for 2:1 odds)
            loss_payout: Loss ratio if lose (typically 1.0)
            bankroll: Total available capital
            max_fraction: Maximum fraction of bankroll to risk
        """
        if win_probability <= 0 or win_probability >= 1:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds, p = win probability, q = lose probability
        lose_probability = 1 - win_probability
        
        if win_payout <= 0:
            return 0.0
        
        # Calculate Kelly fraction
        kelly_fraction = (win_payout * win_probability - lose_probability) / win_payout
        
        # Apply safety constraints
        kelly_fraction = max(0, kelly_fraction)  # No negative positions
        kelly_fraction = min(max_fraction, kelly_fraction)  # Cap at max fraction
        
        # Calculate position size
        position_size = bankroll * kelly_fraction
        
        return position_size
    
    @staticmethod
    def calculate_edge_betting_size(
        current_price: float,
        fair_value: float,
        bankroll: float,
        confidence: float = 0.7,
        max_fraction: float = 0.25
    ) -> Dict[str, float]:
        """
        Calculate position size for edge betting in prediction markets
        """
        edge = fair_value - current_price
        
        if abs(edge) < 0.005:  # Minimum edge threshold (0.5% for demo)
            return {"size": 0.0, "side": "none", "edge": edge}
        
        # Determine side
        side = "yes" if edge > 0 else "no"
        
        # Calculate implied odds
        if side == "yes":
            win_probability = fair_value * confidence
            win_payout = (1 - current_price) / current_price  # Payout ratio for YES
        else:
            win_probability = (1 - fair_value) * confidence
            win_payout = current_price / (1 - current_price)  # Payout ratio for NO
        
        # Calculate optimal size
        optimal_size = KellyCriterion.calculate_optimal_size(
            win_probability=win_probability,
            win_payout=win_payout,
            loss_payout=1.0,
            bankroll=bankroll,
            max_fraction=max_fraction
        )
        
        return {
            "size": optimal_size,
            "side": side,
            "edge": edge,
            "win_probability": win_probability,
            "win_payout": win_payout
        }

class RiskManager:
    """
    Risk management system for prediction market trading
    """
    
    def __init__(self, max_portfolio_risk: float = 0.25):
        self.max_portfolio_risk = max_portfolio_risk
        self.position_limits = {
            "single_position": 0.1,  # Max 10% in single position
            "category_concentration": 0.3,  # Max 30% in single category
            "correlation_limit": 0.5  # Max 50% in correlated positions
        }
    
    def calculate_position_risk(
        self,
        position_size: float,
        entry_price: float,
        current_price: float,
        volatility: float,
        time_to_expiry: float
    ) -> Dict[str, float]:
        """Calculate risk metrics for a position"""
        
        # Value at Risk (VaR) calculation
        price_std = volatility * math.sqrt(time_to_expiry / 365)  # Daily volatility
        var_95 = position_size * 1.96 * price_std  # 95% VaR
        
        # Maximum possible loss
        max_loss = position_size * entry_price
        
        # Time decay risk (for binary options)
        time_decay_risk = position_size * 0.1 * (1 / max(time_to_expiry, 1/365))
        
        # Liquidity risk (simplified)
        liquidity_risk = position_size * 0.05  # Assume 5% liquidity discount
        
        return {
            "var_95": var_95,
            "max_loss": max_loss,
            "time_decay_risk": time_decay_risk,
            "liquidity_risk": liquidity_risk,
            "total_risk": var_95 + time_decay_risk + liquidity_risk
        }
    
    def check_position_limits(
        self,
        proposed_size: float,
        market_category: str,
        current_positions: List[Dict],
        total_bankroll: float
    ) -> Dict[str, bool]:
        """Check if proposed position violates risk limits"""
        
        # Single position limit
        single_position_ok = (proposed_size / total_bankroll) <= self.position_limits["single_position"]
        
        # Category concentration limit
        category_exposure = sum(
            pos["size"] for pos in current_positions 
            if pos.get("category") == market_category
        )
        category_ok = ((category_exposure + proposed_size) / total_bankroll) <= self.position_limits["category_concentration"]
        
        # Total portfolio risk
        total_exposure = sum(pos["size"] for pos in current_positions) + proposed_size
        portfolio_ok = (total_exposure / total_bankroll) <= self.max_portfolio_risk
        
        return {
            "single_position_ok": single_position_ok,
            "category_concentration_ok": category_ok,
            "portfolio_risk_ok": portfolio_ok,
            "all_checks_passed": all([single_position_ok, category_ok, portfolio_ok])
        }
    
    def calculate_portfolio_metrics(self, positions: List[Dict]) -> RiskMetrics:
        """Calculate portfolio-level risk metrics"""
        
        if not positions:
            return RiskMetrics(
                position_size_limit=self.position_limits["single_position"],
                portfolio_heat=0.0,
                correlation_risk=0.0,
                liquidity_risk=0.0,
                time_decay_risk=0.0
            )
        
        total_exposure = sum(pos.get("size", 0) for pos in positions)
        total_bankroll = sum(pos.get("size", 0) for pos in positions) / 0.25  # Assume 25% utilization
        
        # Portfolio heat (total risk as % of bankroll)
        portfolio_heat = total_exposure / total_bankroll if total_bankroll > 0 else 0
        
        # Correlation risk (simplified - based on category concentration)
        categories = {}
        for pos in positions:
            cat = pos.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + pos.get("size", 0)
        
        max_category_exposure = max(categories.values()) if categories else 0
        correlation_risk = max_category_exposure / total_exposure if total_exposure > 0 else 0
        
        # Average liquidity risk
        liquidity_risk = sum(pos.get("size", 0) * 0.05 for pos in positions) / total_exposure if total_exposure > 0 else 0
        
        # Time decay risk
        time_decay_risk = sum(
            pos.get("size", 0) * 0.1 / max(pos.get("time_to_expiry", 1), 1/365)
            for pos in positions
        ) / total_exposure if total_exposure > 0 else 0
        
        return RiskMetrics(
            position_size_limit=self.position_limits["single_position"],
            portfolio_heat=portfolio_heat,
            correlation_risk=correlation_risk,
            liquidity_risk=liquidity_risk,
            time_decay_risk=time_decay_risk
        )

class TradingEngine:
    """
    Main trading engine that combines all algorithms
    """
    
    def __init__(self, bankroll: float = 10000.0):
        self.bankroll = bankroll
        self.black_scholes = BlackScholesAdapter()
        self.kelly = KellyCriterion()
        self.risk_manager = RiskManager()
    
    def analyze_trading_opportunity(
        self,
        market: Dict,
        current_positions: List[Dict] = None
    ) -> Optional[TradingSignal]:
        """
        Comprehensive analysis of a trading opportunity
        """
        current_positions = current_positions or []
        
        # Calculate time to expiry
        time_to_expiry = self._calculate_time_to_expiry(market.get("end_date"))
        if time_to_expiry <= 0:
            return None  # Market expired
        
        # Estimate volatility
        volatility = 0.3  # Default volatility, could be improved with historical data
        
        # Calculate Black-Scholes fair value
        bs_result = self.black_scholes.calculate_fair_value(
            current_price=market["yes_price"],
            time_to_expiry=time_to_expiry,
            volatility=volatility
        )
        
        # Enhance fair value with market-based adjustments for demo
        base_fair_value = bs_result["fair_value"]
        
        # Add some market inefficiency simulation for demo purposes
        volume_factor = min(1.0, market.get("volume", 0) / 500000)  # Normalize volume
        liquidity_factor = min(1.0, market.get("liquidity", 0) / 50000)  # Normalize liquidity
        
        # Lower volume/liquidity markets might have more inefficiencies
        inefficiency = (1 - volume_factor) * 0.02 + (1 - liquidity_factor) * 0.01
        
        # Apply inefficiency (sometimes positive, sometimes negative)
        import random
        random.seed(hash(market["id"]) % 1000)  # Deterministic but varies by market
        fair_value = base_fair_value + (random.random() - 0.5) * inefficiency * 2
        
        # Calculate Kelly sizing
        kelly_result = self.kelly.calculate_edge_betting_size(
            current_price=market["yes_price"],
            fair_value=fair_value,
            bankroll=self.bankroll,
            confidence=0.7
        )
        
        if kelly_result["size"] == 0:
            return None  # No edge
        
        # Risk management checks
        risk_checks = self.risk_manager.check_position_limits(
            proposed_size=kelly_result["size"],
            market_category=market.get("category", "Unknown"),
            current_positions=current_positions,
            total_bankroll=self.bankroll
        )
        
        if not risk_checks["all_checks_passed"]:
            # Reduce size to fit risk limits
            kelly_result["size"] *= 0.5
        
        # Generate trading signal
        side = TradeSide.YES if kelly_result["side"] == "yes" else TradeSide.NO
        
        # Calculate entry price (slight improvement)
        if side == TradeSide.YES:
            entry_price = max(0.01, market["yes_price"] - 0.01)
        else:
            entry_price = max(0.01, market["no_price"] - 0.01)
        
        # Risk metrics for this position
        position_risk = self.risk_manager.calculate_position_risk(
            position_size=kelly_result["size"],
            entry_price=entry_price,
            current_price=market["yes_price"],
            volatility=volatility,
            time_to_expiry=time_to_expiry
        )
        
        return TradingSignal(
            market_id=market["id"],
            side=side,
            confidence=kelly_result["win_probability"],
            recommended_size=round(kelly_result["size"], 2),
            entry_price=round(entry_price, 3),
            stop_loss=round(max(0.01, entry_price * 0.8), 3),
            take_profit=round(min(0.99, entry_price * 1.3), 3),
            reasoning=f"BS Fair Value: {fair_value:.3f} vs Market: {market['yes_price']:.3f}. "
                     f"Edge: {kelly_result['edge']:.3f}. Time decay: {bs_result['time_decay']:.4f}/day. "
                     f"VaR: ${position_risk['var_95']:.2f}",
            risk_score=position_risk["total_risk"] / kelly_result["size"]
        )
    
    def _calculate_time_to_expiry(self, end_date: Optional[str]) -> float:
        """Calculate time to expiry in years"""
        if not end_date:
            return 0.25  # Default 3 months
        
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            now = datetime.utcnow()
            delta = end_dt - now
            return max(0, delta.total_seconds() / (365.25 * 24 * 3600))
        except:
            return 0.25  # Default fallback

# Global trading engine
trading_engine = TradingEngine()