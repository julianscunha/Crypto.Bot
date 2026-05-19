# -*- coding: utf-8 -*-

from typing import (
    List,
    Dict
)

from pydantic import (
    BaseModel
)

from apps.api.schemas.metrics_schema import (
    MetricsResponse
)

from apps.api.schemas.portfolio_schema import (
    PortfolioResponse
)

from apps.api.schemas.trade_schema import (
    TradeResponse
)

# =====================================================
# RUNTIME RESPONSE
# =====================================================

class RuntimeResponse(
    BaseModel
):

    # =================================================
    # CONNECTION
    # =================================================

    websocket_connected: bool

    # =================================================
    # MARKET INGESTION
    # =================================================

    total_messages: int

    active_symbols: List[str]

    # =================================================
    # ANALYSIS PIPELINE
    # =================================================

    total_analysis_requests: int = 0

    total_generated_signals: int = 0

    total_approved_signals: int = 0

    total_rejected_signals: int = 0

    # =================================================
    # EXECUTION PIPELINE
    # =================================================

    total_executed_orders: int = 0

    total_closed_positions: int = 0

    # =================================================
    # TELEMETRY
    # =================================================

    blocked_signal_reasons: Dict[
        str,
        int
    ] = {}

    execution_reasons: Dict[
        str,
        int
    ] = {}

    # =================================================
    # METRICS
    # =================================================

    signal_generation_ratio: float = 0.0

    signal_approval_ratio: float = 0.0

    execution_ratio: float = 0.0

    uptime_seconds: int = 0

# =====================================================
# DASHBOARD RESPONSE
# =====================================================

class DashboardResponse(
    BaseModel
):

    runtime: RuntimeResponse

    metrics: MetricsResponse

    portfolio: PortfolioResponse

    open_trades: List[
        TradeResponse
    ]

    recent_closed_trades: List[
        TradeResponse
    ]