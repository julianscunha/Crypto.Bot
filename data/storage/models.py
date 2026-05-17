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

    DeclarativeBase,

    Mapped,

    mapped_column
)

# =====================================================
# BASE
# =====================================================

class Base(
    DeclarativeBase
):

    pass

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )