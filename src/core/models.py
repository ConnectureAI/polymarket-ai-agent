from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class TradeSide(str, Enum):
    YES = "yes"
    NO = "no"

class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"

class Market(BaseModel):
    id: str
    question: str
    end_date: Optional[str] = None
    category: Optional[str] = None
    volume: float = 0.0
    liquidity: float = 0.0
    yes_price: float = 0.5
    no_price: float = 0.5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def implied_probability(self) -> float:
        return self.yes_price
    
    @property
    def time_to_expiry(self) -> Optional[float]:
        if not self.end_date:
            return None
        try:
            end_dt = datetime.fromisoformat(self.end_date.replace('Z', '+00:00'))
            now = datetime.utcnow()
            return (end_dt - now).total_seconds() / (365.25 * 24 * 3600)  # Years
        except:
            return None

class Position(BaseModel):
    id: Optional[int] = None
    market_id: str
    side: TradeSide
    size: float
    entry_price: float
    current_price: Optional[float] = None
    pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Market info (populated from joins)
    question: Optional[str] = None
    category: Optional[str] = None
    
    def calculate_pnl(self, current_price: float) -> float:
        if self.side == TradeSide.YES:
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size

class Trade(BaseModel):
    id: Optional[int] = None
    market_id: str
    side: TradeSide
    size: float
    price: float
    fee: float = 0.0
    timestamp: Optional[datetime] = None
    
    # Market info (populated from joins)
    question: Optional[str] = None
    category: Optional[str] = None

class TradingSignal(BaseModel):
    market_id: str
    side: TradeSide
    confidence: float  # 0-1
    recommended_size: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str
    risk_score: float  # 0-1

class PortfolioStats(BaseModel):
    total_pnl: float
    open_positions: int
    total_trades: int
    win_rate: float
    total_closed_positions: int
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    
class MarketAnalysis(BaseModel):
    market_id: str
    fair_value: float
    volatility: float
    trend: str  # "bullish", "bearish", "neutral"
    confidence: float
    key_factors: list[str]
    price_targets: Dict[str, float]  # {"support": 0.4, "resistance": 0.7}
    
class RiskMetrics(BaseModel):
    position_size_limit: float
    portfolio_heat: float  # Total risk as % of portfolio
    correlation_risk: float
    liquidity_risk: float
    time_decay_risk: float