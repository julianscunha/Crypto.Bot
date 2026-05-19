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
    Optional,
    Dict
)

# =========================================================
# BASE PAYLOAD
# =========================================================

@dataclass(slots=True)
class BasePayload:

    user_id: int

    symbol: str

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

    correlation_id: Optional[str] = None

    metadata: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

# =========================================================
# MARKET DATA
# =========================================================

@dataclass(slots=True)
class MarketDataPayload(
    BasePayload
):

    open: float

    high: float

    low: float

    close: float

    volume: float

    timeframe: str = "5m"

    exchange: str = "BINANCE"

# =========================================================
# MARKET DATA MESSAGE
# =========================================================

@dataclass(slots=True)
class MarketDataMessage(
    BaseMessage
):

    payload: MarketDataPayload

# =========================================================
# MARKET ANALYSIS
# =========================================================

@dataclass(slots=True)
class MarketAnalysisPayload(
    BasePayload
):

    analysis: str

    reference_price: float

    confidence: float = 0.0

    market_regime: str = "UNKNOWN"

    trend_strength: float = 0.0

    volatility_regime: str = "UNKNOWN"

# =========================================================
# MARKET ANALYSIS MESSAGE
# =========================================================

@dataclass(slots=True)
class MarketAnalysisMessage(
    BaseMessage
):

    payload: MarketAnalysisPayload

# =========================================================
# STRATEGY SIGNAL
# =========================================================

@dataclass(slots=True)
class StrategySignalPayload(
    BasePayload
):

    signal: str

    entry_price: float

    signal_strength: float = 0.0

    atr: Optional[float] = None

    structure_score: float = 0.0

    trend_strength: float = 0.0

    volatility_regime: str = "UNKNOWN"

    strategy_name: str = "PRIMARY"

# =========================================================
# STRATEGY SIGNAL MESSAGE
# =========================================================

@dataclass(slots=True)
class StrategySignalMessage(
    BaseMessage
):

    payload: StrategySignalPayload

# =========================================================
# RISK DECISION
# =========================================================

@dataclass(slots=True)
class RiskDecisionPayload(
    BasePayload
):

    signal: str

    entry_price: float

    quantity: float

    stop_loss: float

    take_profit: float

    trailing_stop: float

    risk_reward: float = 0.0

    expected_loss: float = 0.0

    expected_profit: float = 0.0

    execution_priority: int = 1

# =========================================================
# RISK DECISION MESSAGE
# =========================================================

@dataclass(slots=True)
class RiskDecisionMessage(
    BaseMessage
):

    payload: RiskDecisionPayload