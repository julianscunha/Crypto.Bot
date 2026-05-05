from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class BaseMessage(BaseModel):
    type: str
    sender: str
    user_id: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    explanation: Optional[str] = None

    class Config:
        extra = "forbid"


# MARKET DATA
class MarketDataPayload(BaseModel):
    symbol: str
    price: float
    open: float
    high: float
    low: float
    volume: float
    closed: bool


class MarketDataMessage(BaseMessage):
    type: str = "MARKET_DATA"
    payload: MarketDataPayload


# MARKET ANALYSIS
class MarketAnalysisPayload(BaseModel):
    trend: str
    volatility: str
    confidence: float


class MarketAnalysisMessage(BaseMessage):
    type: str = "MARKET_ANALYSIS"
    payload: MarketAnalysisPayload


# TRADE PROPOSAL
class TradeProposalPayload(BaseModel):
    action: str
    confidence: float


class TradeProposalMessage(BaseMessage):
    type: str = "TRADE_PROPOSAL"
    payload: TradeProposalPayload


# RISK
class RiskDecisionPayload(BaseModel):
    approved: bool


class RiskDecisionMessage(BaseMessage):
    type: str = "RISK_DECISION"
    payload: RiskDecisionPayload