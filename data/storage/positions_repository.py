# -*- coding: utf-8 -*-

from datetime import datetime

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal

from data.storage.models import Trade


class PositionsRepository:

    def _session(self) -> Session:

        return SessionLocal()

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
        breakeven_enabled: bool = True
    ):

        session = self._session()

        try:

            position = Trade(
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
                pnl=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                highest_price=entry_price,
                lowest_price=entry_price
            )

            session.add(position)

            session.commit()

            session.refresh(position)

            return position

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def get_open_position(
        self,
        user_id: int,
        symbol: str
    ):

        session = self._session()

        try:

            return (
                session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.symbol == symbol,
                    Trade.status == "OPEN"
                )
                .first()
            )

        finally:

            session.close()

    def get_open_positions(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            return (
                session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.status == "OPEN"
                )
                .all()
            )

        finally:

            session.close()

    def has_open_position(
        self,
        user_id: int,
        symbol: str
    ) -> bool:

        position = self.get_open_position(
            user_id=user_id,
            symbol=symbol
        )

        return position is not None

    def update_price(
        self,
        trade_id: int,
        current_price: float,
        unrealized_pnl: float
    ):

        session = self._session()

        try:

            trade = (
                session.query(Trade)
                .filter(
                    Trade.id == trade_id
                )
                .first()
            )

            if not trade:
                return None

            trade.current_price = current_price
            trade.unrealized_pnl = unrealized_pnl

            if current_price > (trade.highest_price or current_price):
                trade.highest_price = current_price

            if current_price < (trade.lowest_price or current_price):
                trade.lowest_price = current_price

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def close_position(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        reason: str
    ):

        session = self._session()

        try:

            trade = (
                session.query(Trade)
                .filter(
                    Trade.id == trade_id
                )
                .first()
            )

            if not trade:
                return None

            trade.current_price = exit_price

            trade.pnl = pnl

            trade.realized_pnl = pnl

            trade.unrealized_pnl = 0.0

            trade.status = "CLOSED"

            trade.exit_reason = reason

            trade.closed_at = datetime.utcnow()

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()