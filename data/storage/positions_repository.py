# -*- coding: utf-8 -*-

from sqlalchemy import select

from data.storage.database import SessionLocal
from data.storage.models import Trade


class PositionsRepository:

    def __init__(self):

        self.db = SessionLocal()

    def create_position(
        self,
        user_id: int,
        symbol: str,
        action: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        trailing_stop: float,
        breakeven_enabled: bool = False
    ):

        trade = Trade(
            user_id=user_id,
            symbol=symbol,
            action=action,

            entry_price=entry_price,
            current_price=entry_price,

            quantity=quantity,

            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,

            breakeven_enabled=breakeven_enabled,

            status="OPEN",
            pnl=0.0
        )

        self.db.add(trade)

        self.db.commit()

        self.db.refresh(trade)

        return trade

    def close_position(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float
    ):

        trade = self.db.get(
            Trade,
            trade_id
        )

        if not trade:
            return

        trade.current_price = exit_price
        trade.pnl = pnl
        trade.status = "CLOSED"

        self.db.commit()

    def get_open_position(
        self,
        user_id: int,
        symbol: str
    ):

        stmt = (
            select(Trade)
            .where(Trade.user_id == user_id)
            .where(Trade.symbol == symbol)
            .where(Trade.status == "OPEN")
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_open_positions(
        self,
        user_id: int
    ):

        stmt = (
            select(Trade)
            .where(Trade.user_id == user_id)
            .where(Trade.status == "OPEN")
        )

        return self.db.execute(stmt).scalars().all()