# -*- coding: utf-8 -*-

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Float
from sqlalchemy import Boolean
from sqlalchemy import DateTime

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime
)


class Base(DeclarativeBase):
    pass


class Trade(Base):

    __tablename__ = "trades"

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
        String,
        nullable=False,
        index=True
    )

    action: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

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

    breakeven_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    exit_reason: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    closed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )
    
class EquityCurve(Base):
    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    equity = Column(
        Float,
        nullable=False
    )

    balance = Column(
        Float,
        nullable=False
    )

    unrealized_pnl = Column(
        Float,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
class PortfolioSnapshot(Base):

    __tablename__ = "portfolio_snapshots"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    balance = Column(
        Float,
        default=0.0
    )

    equity = Column(
        Float,
        default=0.0
    )

    realized_pnl = Column(
        Float,
        default=0.0
    )

    unrealized_pnl = Column(
        Float,
        default=0.0
    )

    total_pnl = Column(
        Float,
        default=0.0
    )

    open_positions = Column(
        Integer,
        default=0
    )

    closed_positions = Column(
        Integer,
        default=0
    )

    exposure = Column(
        Float,
        default=0.0
    )

    drawdown = Column(
        Float,
        default=0.0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )