# -*- coding: utf-8 -*-

from datetime import datetime

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal

from data.storage.models import Trade


class TradesRepository:

    def _session(self) -> Session:

        return SessionLocal()

    # =====================================================
    # CREATE TRADE
    # =====================================================

    def create_trade(
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
                pnl=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                highest_price=entry_price,
                lowest_price=entry_price
            )

            session.add(trade)

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    # =====================================================
    # GET OPEN TRADE
    # =====================================================

    def get_open_trade(
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

    # =====================================================
    # GET OPEN TRADES
    # =====================================================

    def get_open_trades(
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

    # =====================================================
    # HAS OPEN TRADE
    # =====================================================

    def has_open_trade(
        self,
        user_id: int,
        symbol: str
    ) -> bool:

        trade = self.get_open_trade(
            user_id=user_id,
            symbol=symbol
        )

        return trade is not None

    # =====================================================
    # UPDATE TRADE PRICE
    # =====================================================

    def update_trade_price(
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

            # =====================================================
            # PRICE
            # =====================================================

            trade.current_price = current_price

            trade.unrealized_pnl = unrealized_pnl

            # =====================================================
            # HIGHEST PRICE
            # =====================================================

            if (
                trade.highest_price is None
                or current_price > trade.highest_price
            ):

                trade.highest_price = current_price

            # =====================================================
            # LOWEST PRICE
            # =====================================================

            if (
                trade.lowest_price is None
                or current_price < trade.lowest_price
            ):

                trade.lowest_price = current_price

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    # =====================================================
    # CLOSE TRADE
    # =====================================================

    def close_trade(
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

    # =====================================================
    # RESET
    # =====================================================

    def reset(self):

        session = self._session()

        try:

            session.query(Trade).delete()

            session.commit()

        finally:

            session.close()


trades_repository = (
    TradesRepository()
)