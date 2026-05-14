# -*- coding: utf-8 -*-

from fastapi import FastAPI
from datetime import datetime

from core.config.settings import settings
from core.state.market_state import market_state

from data.storage.repositories.portfolio_repository import (
    PortfolioRepository
)

from data.storage.metrics import (
    MetricsStorage
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

from typing import List

from apps.api.schemas.trade_schema import (
    TradeResponse
)

from apps.api.schemas.dashboard_schema import (
    DashboardResponse,
    RuntimeResponse
)

app = FastAPI(
    title="Crypto.Bot API",
    version="1.0.0"
)

portfolio_repository = PortfolioRepository()

metrics_storage = MetricsStorage()

# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "mode": settings.MODE,
        "timestamp": datetime.utcnow()
    }

# =====================================================
# RUNTIME
# =====================================================

@app.get("/runtime")
async def runtime():

    snapshot = (
        market_state.snapshot()
    )

    return {

        "mode": settings.MODE,

        "symbols": settings.SYMBOLS,

        "api_host": settings.API_HOST,

        "api_port": settings.API_PORT,

        "log_level": settings.LOG_LEVEL,

        "runtime": snapshot
    }

# =====================================================
# ROOT
# =====================================================

@app.get("/")
async def root():

    return {
        "name": "Crypto.Bot",
        "status": "running"
    }
    
# =====================================================
# PORTFOLIO
# =====================================================

@app.get(
    "/portfolio",
    response_model=PortfolioResponse
)
async def portfolio():

    snapshot = (
        portfolio_repository
        .get_latest_snapshot(
            user_id=0
        )
    )

    if not snapshot:
    
        return PortfolioResponse(
            balance=0,
            equity=0,
            realized_pnl=0,
            unrealized_pnl=0,
            total_pnl=0,
            open_positions=0,
            closed_positions=0,
            exposure=0,
            drawdown=0,
            created_at=datetime.utcnow()
        )

    return {

        "balance":
            snapshot.balance,

        "equity":
            snapshot.equity,

        "realized_pnl":
            snapshot.realized_pnl,

        "unrealized_pnl":
            snapshot.unrealized_pnl,

        "total_pnl":
            snapshot.total_pnl,

        "open_positions":
            snapshot.open_positions,

        "closed_positions":
            snapshot.closed_positions,

        "exposure":
            snapshot.exposure,

        "drawdown":
            snapshot.drawdown,

        "created_at":
            snapshot.created_at
    }
    
# =====================================================
# METRICS
# =====================================================

@app.get(
    "/metrics",
    response_model=MetricsResponse
)
async def metrics():

    return (
        metrics_storage.get_metrics(
            user_id=0
        )
    )

# =====================================================
# OPEN TRADES
# =====================================================

@app.get(
    "/trades/open",
    response_model=List[TradeResponse]
)
async def open_trades():

    trades = (
        trades_repository
        .get_open_trades(
            user_id=0
        )
    )

    return [

        {
            "id":
                trade.id,

            "symbol":
                trade.symbol,

            "action":
                trade.action,

            "entry_price":
                trade.entry_price,

            "current_price":
                trade.current_price,

            "quantity":
                trade.quantity,

            "pnl":
                trade.pnl,

            "unrealized_pnl":
                trade.unrealized_pnl,

            "status":
                trade.status

        }

        for trade in trades
    ]


# =====================================================
# CLOSED TRADES
# =====================================================

@app.get(
    "/trades/closed",
    response_model=List[TradeResponse]
)
async def closed_trades():

    trades = (
        trades_repository
        .get_closed_trades(
            user_id=0
        )
    )

    return [

        {
            "id":
                trade.id,

            "symbol":
                trade.symbol,

            "action":
                trade.action,

            "entry_price":
                trade.entry_price,

            "current_price":
                trade.current_price,

            "quantity":
                trade.quantity,

            "pnl":
                trade.pnl,

            "realized_pnl":
                trade.realized_pnl,

            "exit_reason":
                trade.exit_reason,

            "status":
                trade.status,

            "created_at":
                trade.created_at,

            "closed_at":
                trade.closed_at

        }

        for trade in trades
    ]
    
# =====================================================
# DASHBOARD
# =====================================================

@app.get(
    "/dashboard",
    response_model=DashboardResponse
)
async def dashboard():

    metrics = (
        metrics_storage.get_metrics(
            user_id=0
        )
    )

    snapshot = (
        portfolio_repository
        .get_latest_snapshot(
            user_id=0
        )
    )

    if not snapshot:

        snapshot = PortfolioResponse(
            balance=0,
            equity=0,
            realized_pnl=0,
            unrealized_pnl=0,
            total_pnl=0,
            open_positions=0,
            closed_positions=0,
            exposure=0,
            drawdown=0,
            created_at=datetime.utcnow()
        )

    else:

        snapshot = PortfolioResponse(
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

    open_trades_data = (
        trades_repository.get_open_trades(
            user_id=0
        )
    )

    closed_trades_data = (
        trades_repository.get_closed_trades(
            user_id=0
        )
    )

    open_trades = [

        TradeResponse(
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

        for trade in open_trades_data
    ]

    recent_closed_trades = [

        TradeResponse(
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

        for trade in closed_trades_data[-5:]
    ]

    runtime = RuntimeResponse(
        websocket_connected=False,
        total_messages=0,
        active_symbols=[]
    )

    return DashboardResponse(
        runtime=runtime,
        metrics=MetricsResponse(**metrics),
        portfolio=snapshot,
        open_trades=open_trades,
        recent_closed_trades=recent_closed_trades
    )