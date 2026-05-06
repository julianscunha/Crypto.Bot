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
    signal: str
    price: float


@dataclass
class StrategySignalMessage(BaseMessage):
    payload: StrategySignalPayload


# =========================================================
# RISK
# =========================================================

@dataclass
class RiskDecisionPayload:
    action: str
    approved: bool
    price: float
    quantity: float
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass
class RiskDecisionMessage(BaseMessage):
    payload: RiskDecisionPayload