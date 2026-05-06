# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Any


# =========================================================
# BASE
# =========================================================

@dataclass
class BaseMessage:
    user_id: int
    payload: Any


# =========================================================
# MARKET
# =========================================================

@dataclass
class MarketDataPayload:
    symbol: str
    price: float


@dataclass
class MarketDataMessage(BaseMessage):
    payload: MarketDataPayload


# =========================================================
# ANALYSIS
# =========================================================

@dataclass
class MarketAnalysisPayload:
    symbol: str
    trend: str
    confidence: float
    price: float


@dataclass
class MarketAnalysisMessage(BaseMessage):
    payload: MarketAnalysisPayload


# =========================================================
# STRATEGY
# =========================================================

@dataclass
class StrategySignalPayload:
    symbol: str
    signal: str
    price: float
    atr: float


@dataclass
class StrategySignalMessage(BaseMessage):
    payload: StrategySignalPayload


# =========================================================
# RISK
# =========================================================

@dataclass
class RiskDecisionPayload:
    symbol: str

    action: str
    approved: bool

    price: float
    quantity: float

    stop_loss: float | None = None
    take_profit: float | None = None

    trailing_stop: float | None = None

    atr: float | None = None

    breakeven_enabled: bool = False


@dataclass
class RiskDecisionMessage(BaseMessage):
    payload: RiskDecisionPayload