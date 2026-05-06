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
    close: float
    high: float
    low: float

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

    price: float


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

    price: float


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

    price: float

    quantity: float

    stop_loss: float
    take_profit: float

    trailing_stop: float


@dataclass
class RiskDecisionMessage(BaseMessage):
    pass