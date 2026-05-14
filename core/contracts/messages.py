# -*- coding: utf-8 -*-

from dataclasses import dataclass


# =========================================================
# BASE MESSAGE
# =========================================================

@dataclass
class BaseMessage:

    sender: str
    payload: object


# =========================================================
# MARKET DATA
# =========================================================

@dataclass
class MarketDataPayload:

    user_id: int

    symbol: str

    open: float
    high: float
    low: float
    close: float

    volume: float


@dataclass
class MarketDataMessage(BaseMessage):
    pass


# =========================================================
# MARKET ANALYSIS
# =========================================================

@dataclass
class MarketAnalysisPayload:

    user_id: int

    symbol: str

    analysis: str

    reference_price: float

    confidence: float


@dataclass
class MarketAnalysisMessage(BaseMessage):
    pass


# =========================================================
# STRATEGY SIGNAL
# =========================================================

@dataclass
class StrategySignalPayload:

    user_id: int

    symbol: str

    signal: str

    entry_price: float

    signal_strength: float
    
    atr: float | None = None

@dataclass
class StrategySignalMessage(BaseMessage):
    pass


# =========================================================
# RISK DECISION
# =========================================================

@dataclass
class RiskDecisionPayload:

    user_id: int

    symbol: str

    signal: str

    entry_price: float

    quantity: float

    stop_loss: float
    take_profit: float

    trailing_stop: float

    risk_reward: float


@dataclass
class RiskDecisionMessage(BaseMessage):
    pass
    


