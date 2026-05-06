# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal
from data.storage.models import Trade


class PositionsRepository:

    def __init__(self):

        self.db: Session = SessionLocal()

    def create_position(
        self,
        user_id: int,
        symbol: str,
        action: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        trailing_stop: float
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
            status="OPEN",
            pnl=0
        )

        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        return trade

    def get_open_position(
        self,
        user_id: int,
        symbol: str
    ):

        return (
            self.db.query(Trade)
            .filter(
                Trade.user_id == user_id,
                Trade.symbol == symbol,
                Trade.status == "OPEN"
            )
            .first()
        )

    def close_position(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float
    ):

        trade = (
            self.db.query(Trade)
            .filter(Trade.id == trade_id)
            .first()
        )

        if not trade:
            return

        trade.current_price = exit_price
        trade.pnl = pnl
        trade.status = "CLOSED"

        self.db.commit()

    def update_price(
        self,
        trade_id: int,
        price: float
    ):

        trade = (
            self.db.query(Trade)
            .filter(Trade.id == trade_id)
            .first()
        )

        if not trade:
            return

        trade.current_price = price

        self.db.commit()