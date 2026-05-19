# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

from sqlalchemy.orm import (
    Session
)

from sqlalchemy import (
    desc
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    Trade
)


class TradesRepository:

    def __init__(self):

        pass

    # =====================================================
    # SESSION
    # =====================================================

    def _session(
        self
    ) -> Session:

        return SessionLocal()

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _is_valid_price(
        value: float
    ) -> bool:

        return (
            value is not None
            and
            value > 0
        )

    @staticmethod
    def _is_valid_quantity(
        value: float
    ) -> bool:

        return (
            value is not None
            and
            value > 0
        )

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

        # =================================================
        # VALIDATION
        # =================================================

        if not self._is_valid_price(
            entry_price
        ):

            return None

        if not self._is_valid_quantity(
            quantity
        ):

            return None

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

            session.add(
                trade
            )

            session.commit()

            session.refresh(
                trade
            )

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    # =====================================================
    # GET TRADE
    # =====================================================

    def get_trade(
        self,
        trade_id: int
    ):

        session = self._session()

        try:

            return (

                session.query(Trade)

                .filter(
                    Trade.id == trade_id
                )

                .first()
            )

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

                .order_by(
                    desc(Trade.id)
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

                .order_by(
                    desc(Trade.id)
                )

                .all()
            )

        finally:

            session.close()

    # =====================================================
    # GET CLOSED TRADES
    # =====================================================

    def get_closed_trades(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            return (

                session.query(Trade)

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "CLOSED"
                )

                .order_by(
                    desc(Trade.closed_at)
                )

                .all()
            )

        finally:

            session.close()

    # =====================================================
    # POSITION EXISTS
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

        if not self._is_valid_price(
            current_price
        ):

            return None

        session = self._session()

        try:

            trade = self.get_trade(
                trade_id
            )

            if not trade:

                return None

            managed_trade = session.merge(
                trade
            )

            # =================================================
            # PRICE
            # =================================================

            managed_trade.current_price = (
                current_price
            )

            managed_trade.unrealized_pnl = (
                unrealized_pnl
            )

            # =================================================
            # HIGH WATERMARK
            # =================================================

            if (

                managed_trade.highest_price is None

                or

                current_price
                >
                managed_trade.highest_price
            ):

                managed_trade.highest_price = (
                    current_price
                )

            # =================================================
            # LOW WATERMARK
            # =================================================

            if (

                managed_trade.lowest_price is None

                or

                current_price
                <
                managed_trade.lowest_price
            ):

                managed_trade.lowest_price = (
                    current_price
                )

            session.commit()

            session.refresh(
                managed_trade
            )

            return managed_trade

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

        if not self._is_valid_price(
            exit_price
        ):

            return None

        session = self._session()

        try:

            trade = self.get_trade(
                trade_id
            )

            if not trade:

                return None

            managed_trade = session.merge(
                trade
            )

            managed_trade.current_price = (
                exit_price
            )

            managed_trade.pnl = pnl

            managed_trade.realized_pnl = pnl

            managed_trade.unrealized_pnl = 0.0

            managed_trade.status = "CLOSED"

            managed_trade.exit_reason = (
                reason
            )

            managed_trade.closed_at = (
                datetime.utcnow()
            )

            session.commit()

            session.refresh(
                managed_trade
            )

            return managed_trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        session = self._session()

        try:

            session.query(
                Trade
            ).delete()

            session.commit()

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()


trades_repository = (
    TradesRepository()
)