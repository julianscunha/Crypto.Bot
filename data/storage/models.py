# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

from sqlalchemy import (

    Integer,

    String,

    Float,

    Boolean,

    DateTime,

    Index
)

from sqlalchemy.orm import (

    Mapped,

    mapped_column
)

from data.storage.database import (
    Base
)

# =====================================================
# BASE
# =====================================================
#
# Base is shared with data.storage.database so that
# Base.metadata.create_all() in init_db() actually registers
# these tables. Two separate DeclarativeBase classes here and
# in database.py would silently produce two disconnected
# metadata registries, leaving init_db() unable to create any
# of these tables on a fresh database.

# =====================================================
# TRADE
# =====================================================

class Trade(
    Base
):

    __tablename__ = "trades"

    # =================================================
    # INDEXES
    # =================================================

    __table_args__ = (

        Index(
            "idx_trade_user_status",
            "user_id",
            "status"
        ),

        Index(
            "idx_trade_symbol_status",
            "symbol",
            "status"
        ),
    )

    # =================================================
    # IDENTIFICATION
    # =================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    action: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    # =================================================
    # PRICING
    # =================================================

    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    current_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    stop_loss: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    take_profit: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    trailing_stop: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    highest_price: Mapped[float] = mapped_column(
        Float,
        nullable=True
    )

    lowest_price: Mapped[float] = mapped_column(
        Float,
        nullable=True
    )

    # =================================================
    # RISK
    # =================================================

    breakeven_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    take_profit_extended: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # =================================================
    # PNL
    # =================================================

    pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    # =================================================
    # LIVE ORDER TRACKING
    # =================================================
    #
    # Real Binance order identifiers -- NULL for PAPER trades,
    # which never place a real order. See migration
    # add_live_order_tracking_columns for the full rationale on why
    # these are needed before LIVE exits can touch the exchange
    # instead of only updating this local row.

    entry_order_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True
    )

    order_list_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True
    )

    # =================================================
    # EXIT
    # =================================================

    exit_reason: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    # =================================================
    # TIMESTAMPS
    # =================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

# =====================================================
# EQUITY CURVE
# =====================================================

class EquityCurve(
    Base
):

    __tablename__ = "equity_curve"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True
    )

    equity: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    balance: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

# =====================================================
# PORTFOLIO SNAPSHOT
# =====================================================

class PortfolioSnapshot(
    Base
):

    __tablename__ = "portfolio_snapshots"

    __table_args__ = (

        Index(
            "idx_snapshot_user_created",
            "user_id",
            "created_at"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True
    )

    balance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    total_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    open_positions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    closed_positions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    drawdown: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    # =================================================
    # SESSION SCOPING
    # =================================================
    #
    # Records the account_balance the bot was configured with at
    # the time of this snapshot. PortfolioService uses this to
    # scope "historical peak equity" (for drawdown %) to snapshots
    # from the SAME configuration -- without it, deliberately
    # resetting the paper account (e.g. lowering account_balance
    # from 100 to 10 in core/config/trading_config.py) gets
    # misread as a 90% real trading loss, since the old $100 peak
    # would otherwise still count as "historical" against a new
    # $10 baseline that was never actually $100.

    initial_balance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

# =====================================================
# RUNTIME STATE
# =====================================================
#
# Single-row table (always id=1, upserted) sharing live market/
# runtime telemetry between OS processes. apps/trader/runner.py
# (the Binance WebSocket + agent pipeline) and apps/api/main.py
# (the FastAPI dashboard backend) run as SEPARATE subprocesses under
# Full Stack -- they do not share memory. core.state.market_state's
# MarketState class is an in-memory singleton, so without this
# table, websocket_connected/active_symbols/signal counters written
# by the Runner process are invisible to the API process forever,
# and the dashboard's "FEED DOWN" / signal pipeline panels never
# reflect reality regardless of how long the bot has been running.
#
# JSON columns (active_symbols, blocked_signal_reasons,
# execution_reasons) are simple enough here that normalizing them
# into separate tables would add complexity without real benefit at
# this scale -- this is small, frequently-overwritten telemetry, not
# an audit trail.

class RuntimeState(
    Base
):

    __tablename__ = "runtime_state"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    websocket_connected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    total_market_messages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    last_market_message_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    active_symbols_json: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="[]"
    )

    total_analysis_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    total_generated_signals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    total_approved_signals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    total_rejected_signals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    total_executed_orders: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    total_closed_positions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    blocked_signal_reasons_json: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        default="{}"
    )

    execution_reasons_json: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        default="{}"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
