import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from core.models import Position, Market, RiskMetrics
from core.config import settings

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Comprehensive risk management system for prediction market trading
    """
    
    def __init__(self):
        self.max_portfolio_risk = settings.risk_tolerance
        self.max_position_size = settings.max_position_size
        self.position_limits = {
            "single_position": 0.1,  # Max 10% in single position
            "category_concentration": 0.3,  # Max 30% in single category
            "correlation_limit": 0.5,  # Max 50% in correlated positions
            "time_decay_limit": 0.2,  # Max 20% in positions expiring < 7 days
            "liquidity_threshold": 1000,  # Minimum liquidity for position
        }
        
        # Circuit breakers
        self.circuit_breakers = {
            "daily_loss_limit": 0.05,  # Max 5% daily loss
            "consecutive_losses": 5,  # Max 5 consecutive losses
            "drawdown_limit": 0.2,  # Max 20% drawdown
        }
        
        # Risk state tracking
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.max_drawdown = 0.0
        self.last_reset = datetime.now().date()
        
    def reset_daily_counters(self):
        """Reset daily risk counters"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.last_reset = today
            logger.info("Daily risk counters reset")
    
    def check_circuit_breakers(self, current_portfolio_value: float) -> Dict[str, bool]:
        """Check if any circuit breakers are triggered"""
        self.reset_daily_counters()
        
        # Daily loss limit
        daily_loss_exceeded = (self.daily_pnl / current_portfolio_value) < -self.circuit_breakers["daily_loss_limit"]
        
        # Consecutive losses
        consecutive_losses_exceeded = self.consecutive_losses >= self.circuit_breakers["consecutive_losses"]
        
        # Drawdown limit
        drawdown_exceeded = self.max_drawdown > self.circuit_breakers["drawdown_limit"]
        
        breakers = {
            "daily_loss_limit": daily_loss_exceeded,
            "consecutive_losses": consecutive_losses_exceeded,
            "drawdown_limit": drawdown_exceeded,
            "any_triggered": any([daily_loss_exceeded, consecutive_losses_exceeded, drawdown_exceeded])
        }
        
        if breakers["any_triggered"]:
            logger.warning(f"Circuit breaker triggered: {breakers}")
        
        return breakers
    
    def assess_position_risk(
        self,
        market: Dict,
        position_size: float,
        current_positions: List[Dict],
        portfolio_value: float
    ) -> Dict[str, any]:
        """Comprehensive position risk assessment"""
        
        risk_assessment = {
            "approved": True,
            "warnings": [],
            "violations": [],
            "risk_score": 0.0,
            "recommended_size": position_size,
            "risk_metrics": {}
        }
        
        # 1. Position size limits
        position_percentage = position_size / portfolio_value
        if position_percentage > self.position_limits["single_position"]:
            risk_assessment["violations"].append(f"Position size ({position_percentage:.1%}) exceeds limit ({self.position_limits['single_position']:.1%})")
            risk_assessment["approved"] = False
        
        # 2. Category concentration
        category = market.get("category", "Unknown")
        category_exposure = sum(
            pos.get("size", 0) for pos in current_positions 
            if pos.get("category") == category
        )
        category_percentage = (category_exposure + position_size) / portfolio_value
        
        if category_percentage > self.position_limits["category_concentration"]:
            risk_assessment["violations"].append(f"Category concentration ({category_percentage:.1%}) exceeds limit")
            risk_assessment["approved"] = False
            # Reduce size to fit within limits
            max_allowed = (self.position_limits["category_concentration"] * portfolio_value) - category_exposure
            risk_assessment["recommended_size"] = max(0, max_allowed)
        
        # 3. Liquidity check
        liquidity = market.get("liquidity", 0)
        if liquidity < self.position_limits["liquidity_threshold"]:
            risk_assessment["warnings"].append(f"Low liquidity (${liquidity:,.0f})")
            risk_assessment["risk_score"] += 0.2
        
        # 4. Time decay risk
        time_to_expiry = self._calculate_time_to_expiry(market.get("end_date"))
        if time_to_expiry < 7:  # Less than 7 days
            risk_assessment["warnings"].append(f"High time decay risk ({time_to_expiry:.1f} days)")
            risk_assessment["risk_score"] += 0.3
        
        # 5. Price impact assessment
        price_impact = self._estimate_price_impact(position_size, liquidity)
        if price_impact > 0.02:  # 2% price impact
            risk_assessment["warnings"].append(f"High price impact ({price_impact:.1%})")
            risk_assessment["risk_score"] += 0.1
        
        # 6. Correlation risk (simplified)
        correlation_risk = self._assess_correlation_risk(market, current_positions)
        if correlation_risk > 0.7:
            risk_assessment["warnings"].append("High correlation with existing positions")
            risk_assessment["risk_score"] += 0.2
        
        # 7. Volatility risk
        volatility = self._estimate_volatility(market)
        if volatility > 0.5:
            risk_assessment["warnings"].append(f"High volatility ({volatility:.1%})")
            risk_assessment["risk_score"] += 0.1
        
        # Calculate overall risk metrics
        risk_assessment["risk_metrics"] = {
            "position_percentage": position_percentage,
            "category_concentration": category_percentage,
            "liquidity_score": min(1.0, liquidity / 10000),
            "time_decay_score": max(0.0, 1.0 - time_to_expiry / 30),
            "price_impact": price_impact,
            "correlation_risk": correlation_risk,
            "volatility": volatility
        }
        
        # Final approval decision
        if risk_assessment["risk_score"] > 0.7:
            risk_assessment["approved"] = False
            risk_assessment["violations"].append("Overall risk score too high")
        
        return risk_assessment
    
    def _calculate_time_to_expiry(self, end_date: Optional[str]) -> float:
        """Calculate time to expiry in days"""
        if not end_date:
            return 30.0  # Default 30 days
        
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            now = datetime.utcnow()
            delta = end_dt - now
            return max(0, delta.total_seconds() / (24 * 3600))
        except:
            return 30.0
    
    def _estimate_price_impact(self, position_size: float, liquidity: float) -> float:
        """Estimate price impact of position"""
        if liquidity <= 0:
            return 0.1  # High impact for no liquidity
        
        # Simple linear model: impact = position_size / liquidity
        return min(0.1, position_size / liquidity)
    
    def _assess_correlation_risk(self, market: Dict, current_positions: List[Dict]) -> float:
        """Assess correlation risk with existing positions"""
        if not current_positions:
            return 0.0
        
        # Simple correlation based on category matching
        category = market.get("category", "Unknown")
        same_category_count = sum(
            1 for pos in current_positions 
            if pos.get("category") == category
        )
        
        # Return correlation score (0-1)
        return min(1.0, same_category_count / len(current_positions))
    
    def _estimate_volatility(self, market: Dict) -> float:
        """Estimate market volatility"""
        yes_price = market.get("yes_price", 0.5)
        
        # Price extremes suggest higher volatility
        price_extremity = abs(yes_price - 0.5) * 2
        
        # Volume-based volatility (higher volume = lower volatility)
        volume = market.get("volume", 0)
        volume_factor = 1.0 - min(1.0, volume / 1000000)  # Normalize to 1M
        
        # Combine factors
        volatility = (price_extremity * 0.3 + volume_factor * 0.7)
        return max(0.1, min(1.0, volatility))
    
    def update_position_outcome(self, position_pnl: float):
        """Update risk tracking based on position outcome"""
        self.daily_pnl += position_pnl
        
        if position_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Update drawdown
        if self.daily_pnl < 0:
            self.max_drawdown = max(self.max_drawdown, abs(self.daily_pnl))
    
    def get_risk_report(self, positions: List[Dict], portfolio_value: float) -> Dict:
        """Generate comprehensive risk report"""
        self.reset_daily_counters()
        
        if not positions:
            return {
                "total_exposure": 0.0,
                "position_count": 0,
                "category_breakdown": {},
                "risk_metrics": RiskMetrics(
                    position_size_limit=self.position_limits["single_position"],
                    portfolio_heat=0.0,
                    correlation_risk=0.0,
                    liquidity_risk=0.0,
                    time_decay_risk=0.0
                ).dict(),
                "circuit_breakers": self.check_circuit_breakers(portfolio_value),
                "recommendations": []
            }
        
        # Calculate exposures
        total_exposure = sum(pos.get("size", 0) for pos in positions)
        portfolio_heat = total_exposure / portfolio_value if portfolio_value > 0 else 0
        
        # Category breakdown
        category_breakdown = {}
        for pos in positions:
            category = pos.get("category", "Unknown")
            category_breakdown[category] = category_breakdown.get(category, 0) + pos.get("size", 0)
        
        # Risk metrics
        risk_metrics = RiskMetrics(
            position_size_limit=self.position_limits["single_position"],
            portfolio_heat=portfolio_heat,
            correlation_risk=self._calculate_portfolio_correlation(positions),
            liquidity_risk=self._calculate_liquidity_risk(positions),
            time_decay_risk=self._calculate_time_decay_risk(positions)
        ).dict()
        
        # Generate recommendations
        recommendations = []
        if portfolio_heat > 0.8:
            recommendations.append("Consider reducing position sizes - portfolio heat is high")
        
        if risk_metrics["correlation_risk"] > 0.7:
            recommendations.append("Diversify across different categories - correlation risk is high")
        
        if risk_metrics["time_decay_risk"] > 0.6:
            recommendations.append("Consider closing positions with high time decay")
        
        if risk_metrics["liquidity_risk"] > 0.5:
            recommendations.append("Review positions in low-liquidity markets")
        
        return {
            "total_exposure": total_exposure,
            "position_count": len(positions),
            "category_breakdown": category_breakdown,
            "risk_metrics": risk_metrics,
            "circuit_breakers": self.check_circuit_breakers(portfolio_value),
            "recommendations": recommendations
        }
    
    def _calculate_portfolio_correlation(self, positions: List[Dict]) -> float:
        """Calculate overall portfolio correlation"""
        if len(positions) <= 1:
            return 0.0
        
        # Group by category
        categories = {}
        for pos in positions:
            category = pos.get("category", "Unknown")
            categories[category] = categories.get(category, 0) + pos.get("size", 0)
        
        # Calculate concentration
        total_size = sum(categories.values())
        if total_size == 0:
            return 0.0
        
        # Herfindahl index (concentration measure)
        hhi = sum((size / total_size) ** 2 for size in categories.values())
        return hhi
    
    def _calculate_liquidity_risk(self, positions: List[Dict]) -> float:
        """Calculate portfolio liquidity risk"""
        if not positions:
            return 0.0
        
        total_size = sum(pos.get("size", 0) for pos in positions)
        if total_size == 0:
            return 0.0
        
        # Weighted average of liquidity scores
        liquidity_scores = []
        for pos in positions:
            liquidity = pos.get("liquidity", 0)
            size = pos.get("size", 0)
            score = 1.0 - min(1.0, liquidity / 10000)  # Invert: higher liquidity = lower risk
            liquidity_scores.append(score * (size / total_size))
        
        return sum(liquidity_scores)
    
    def _calculate_time_decay_risk(self, positions: List[Dict]) -> float:
        """Calculate portfolio time decay risk"""
        if not positions:
            return 0.0
        
        total_size = sum(pos.get("size", 0) for pos in positions)
        if total_size == 0:
            return 0.0
        
        # Weighted average of time decay scores
        time_decay_scores = []
        for pos in positions:
            time_to_expiry = self._calculate_time_to_expiry(pos.get("end_date"))
            size = pos.get("size", 0)
            score = max(0.0, 1.0 - time_to_expiry / 30)  # Higher risk for shorter time
            time_decay_scores.append(score * (size / total_size))
        
        return sum(time_decay_scores)

# Global risk manager instance
risk_manager = RiskManager()