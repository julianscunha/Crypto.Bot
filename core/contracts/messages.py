# -*- coding: utf-8 -*-

from dataclasses import (
    dataclass,
    field
)

from datetime import (
    datetime
)

from typing import (
    Any,
    Optional
)

# =========================================================
# BASE MESSAGE
# =========================================================

@dataclass(slots=True)
class BaseMessage:

    sender: str

    payload: Any

    created_at: datetime = field(
        default_factory=datetime.utcnow
    )

# =========================================================
# MARKET DATA
# =========================================================

@dataclass(slots=True)
class MarketDataPayload:

    user_id: int

    symbol: str

    open: float

    high: float

    low: float

    close: float

    volume: float


@dataclass(slots=True)
class MarketDataMessage(
    BaseMessage
):

    pass

# =========================================================
# MARKET ANALYSIS
# =========================================================

@dataclass(slots=True)
class MarketAnalysisPayload:

    user_id: int

    symbol: str

    analysis: str

    reference_price: float

    confidence: float = 0.0


@dataclass(slots=True)
class MarketAnalysisMessage(
    BaseMessage
):

    pass

# =========================================================
# STRATEGY SIGNAL
# =========================================================

@dataclass(slots=True)
class StrategySignalPayload:

    user_id: int

    symbol: str

    signal: str

    entry_price: float

    signal_strength: float = 0.0

    atr: Optional[float] = None


@dataclass(slots=True)
class StrategySignalMessage(
    BaseMessage
):

    pass

# =========================================================
# RISK DECISION
# =========================================================

@dataclass(slots=True)
class RiskDecisionPayload:

    user_id: int

    symbol: str

    signal: str

    entry_price: float

    quantity: float

    stop_loss: float

    take_profit: float

    trailing_stop: float

    risk_reward: float = 0.0


@dataclass(slots=True)
class RiskDecisionMessage(
    BaseMessage
):

    pass