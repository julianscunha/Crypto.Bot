# -*- coding: utf-8 -*-

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    TIMESTAMP
)

from sqlalchemy.sql import func

from data.storage.database import Base


class Trade(Base):

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=False)

    symbol = Column(String, nullable=False)

    action = Column(String, nullable=False)

    entry_price = Column(Float, nullable=False)

    current_price = Column(Float, nullable=False)

    quantity = Column(Float, nullable=False)

    stop_loss = Column(Float)

    take_profit = Column(Float)

    trailing_stop = Column(Float)

    breakeven_enabled = Column(Integer)

    status = Column(String)

    pnl = Column(Float)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now()
    )


class EquityCurve(Base):

    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=False)

    equity = Column(Float)

    realized_pnl = Column(Float)

    unrealized_pnl = Column(Float)

    drawdown = Column(Float)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now()
    )