# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

from typing import (
    List
)

from fastapi import (
    FastAPI
)

from core.config.settings import (
    settings
)

from core.state.market_state import (
    market_state
)

from core.services.trade_metrics_service import (
    trade_metrics_service
)

from data.storage.repositories.portfolio_repository import (
    portfolio_repository
)

from data.storage.repositories.trades_repository import (
    trades_repository
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

from apps.api.schemas.dashboard_schema import (

    DashboardResponse,

    RuntimeResponse
)

# =====================================================
# API
# =====================================================

app = FastAPI(

    title="Crypto.Bot API",

    version="2.1.0"
)

# =====================================================
# CONSTANTS
# =====================================================

DEFAULT_USER_ID = 0

RECENT_CLOSED_TRADES_LIMIT = 5

# =====================================================
# HELPERS
# =====================================================

def build_empty_portfolio_response():

    return PortfolioResponse(

        balance=0.0,

        equity=0.0,

        realized_pnl=0.0,

        unrealized_pnl=0.0,

        total_pnl=0.0,

        open_positions=0,

        closed_positions=0,

        exposure=0.0,

        drawdown=0.0,

        created_at=datetime.utcnow()
    )


def build_open_trade_response(
    trade
):

    return TradeResponse(

        id=trade.id,

        symbol=trade.symbol,

        action=trade.action,

        entry_price=trade.entry_price,

        current_price=trade.current_price,

        quantity=trade.quantity,

        pnl=trade.pnl,

        unrealized_pnl=trade.unrealized_pnl,

        status=trade.status
    )


def build_closed_trade_response(
    trade
):

    return TradeResponse(

        id=trade.id,

        symbol=trade.symbol,

        action=trade.action,

        entry_price=trade.entry_price,

        current_price=trade.current_price,

        quantity=trade.quantity,

        pnl=trade.pnl,

        realized_pnl=trade.realized_pnl,

        exit_reason=trade.exit_reason,

        status=trade.status,

        created_at=trade.created_at,

        closed_at=trade.closed_at
    )


def build_portfolio_response(
    snapshot
):

    if not snapshot:

        return build_empty_portfolio_response()

    return PortfolioResponse(

        balance=snapshot.balance,

        equity=snapshot.equity,

        realized_pnl=snapshot.realized_pnl,

        unrealized_pnl=snapshot.unrealized_pnl,

        total_pnl=snapshot.total_pnl,

        open_positions=snapshot.open_positions,

        closed_positions=snapshot.closed_positions,

        exposure=snapshot.exposure,

        drawdown=snapshot.drawdown,

        created_at=snapshot.created_at
    )


def build_runtime_response():

    runtime_snapshot = (
        market_state.snapshot()
    )

    return RuntimeResponse(

        # =================================================
        # CONNECTION
        # =================================================

        websocket_connected=runtime_snapshot[
            "websocket_connected"
        ],

        # =================================================
        # MARKET INGESTION
        # =================================================

        total_messages=runtime_snapshot[
            "total_market_messages"
        ],

        active_symbols=runtime_snapshot[
            "active_symbols"
        ],

        # =================================================
        # ANALYSIS PIPELINE
        # =================================================

        total_analysis_requests=runtime_snapshot[
            "total_analysis_requests"
        ],

        total_generated_signals=runtime_snapshot[
            "total_generated_signals"
        ],

        total_approved_signals=runtime_snapshot[
            "total_approved_signals"
        ],

        total_rejected_signals=runtime_snapshot[
            "total_rejected_signals"
        ],

        # =================================================
        # EXECUTION PIPELINE
        # =================================================

        total_executed_orders=runtime_snapshot[
            "total_executed_orders"
        ],

        total_closed_positions=runtime_snapshot[
            "total_closed_positions"
        ],

        # =================================================
        # TELEMETRY
        # =================================================

        blocked_signal_reasons=runtime_snapshot[
            "blocked_signal_reasons"
        ],

        execution_reasons=runtime_snapshot[
            "execution_reasons"
        ],

        # =================================================
        # METRICS
        # =================================================

        signal_generation_ratio=runtime_snapshot[
            "signal_generation_ratio"
        ],

        signal_approval_ratio=runtime_snapshot[
            "signal_approval_ratio"
        ],

        execution_ratio=runtime_snapshot[
            "execution_ratio"
        ],

        uptime_seconds=runtime_snapshot[
            "uptime_seconds"
        ]
    )

# =====================================================
# ROOT
# =====================================================

@app.get("/")
async def root():

    return {

        "name": "Crypto.Bot",

        "status": "running",

        "mode": settings.MODE,

        "version": "2.1.0"
    }

# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
async def health():

    runtime_response = (
        build_runtime_response()
    )

    return {

        "status": "ok",

        "mode": settings.MODE,

        "timestamp": datetime.utcnow(),

        "websocket_connected":
            runtime_response.websocket_connected,

        "uptime_seconds":
            runtime_response.uptime_seconds
    }

# =====================================================
# RUNTIME
# =====================================================

@app.get(
    "/runtime",
    response_model=RuntimeResponse
)
async def runtime():

    return build_runtime_response()

# =====================================================
# PORTFOLIO
# =====================================================

@app.get(
    "/portfolio",
    response_model=PortfolioResponse
)
async def portfolio():

    latest_snapshot = (

        portfolio_repository
        .get_latest_snapshot(

            user_id=DEFAULT_USER_ID
        )
    )

    return build_portfolio_response(
        latest_snapshot
    )

# =====================================================
# METRICS
# =====================================================

@app.get(
    "/metrics",
    response_model=MetricsResponse
)
async def metrics():

    metrics_data = (

        trade_metrics_service
        .get_metrics(

            user_id=DEFAULT_USER_ID
        )
    )

    return MetricsResponse(
        **metrics_data
    )

# =====================================================
# OPEN TRADES
# =====================================================

@app.get(
    "/trades/open",
    response_model=List[TradeResponse]
)
async def open_trades():

    open_positions = (

        trades_repository
        .get_open_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    return [

        build_open_trade_response(
            trade
        )

        for trade in open_positions
    ]

# =====================================================
# CLOSED TRADES
# =====================================================

@app.get(
    "/trades/closed",
    response_model=List[TradeResponse]
)
async def closed_trades():

    closed_positions = (

        trades_repository
        .get_closed_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    return [

        build_closed_trade_response(
            trade
        )

        for trade in closed_positions
    ]

# =====================================================
# DASHBOARD
# =====================================================

@app.get(
    "/dashboard",
    response_model=DashboardResponse
)
async def dashboard():

    portfolio_snapshot = (

        portfolio_repository
        .get_latest_snapshot(

            user_id=DEFAULT_USER_ID
        )
    )

    metrics_data = (

        trade_metrics_service
        .get_metrics(

            user_id=DEFAULT_USER_ID
        )
    )

    open_positions = (

        trades_repository
        .get_open_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    closed_positions = (

        trades_repository
        .get_closed_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    return DashboardResponse(

        runtime=build_runtime_response(),

        metrics=MetricsResponse(
            **metrics_data
        ),

        portfolio=build_portfolio_response(
            portfolio_snapshot
        ),

        open_trades=[

            build_open_trade_response(
                trade
            )

            for trade in open_positions
        ],

        recent_closed_trades=[

            build_closed_trade_response(
                trade
            )

            for trade in closed_positions[
                -RECENT_CLOSED_TRADES_LIMIT:
            ]
        ]
    )