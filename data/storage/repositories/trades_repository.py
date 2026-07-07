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
        breakeven_enabled: bool = False,
        entry_order_id: str | None = None,
        order_list_id: str | None = None
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

                entry_order_id=entry_order_id,

                order_list_id=order_list_id,

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
    # DAILY QUERIES
    # =====================================================
    #
    # "Today" is always UTC, matching the UTC timestamps Trade rows
    # are actually written with (created_at/closed_at both default
    # to datetime.utcnow). Used by the daily circuit breakers in
    # core/services/risk_protection_service.py -- mixing local and
    # UTC boundaries here would make "today" silently wrong by
    # several hours depending on the deployment's timezone.

    def get_trades_closed_today(
        self,
        user_id: int
    ):

        today_start = datetime.utcnow().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        session = self._session()

        try:

            return (

                session.query(Trade)

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "CLOSED",

                    Trade.closed_at >= today_start
                )

                .order_by(
                    desc(Trade.closed_at)
                )

                .all()
            )

        finally:

            session.close()

    def count_trades_opened_today(
        self,
        user_id: int
    ) -> int:

        today_start = datetime.utcnow().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        session = self._session()

        try:

            return (

                session.query(Trade)

                .filter(

                    Trade.user_id == user_id,

                    Trade.created_at >= today_start
                )

                .count()
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
    # UPDATE STOP LOSS
    # =====================================================
    #
    # Used by PositionManagerAgent's breakeven logic to move a
    # position's stop_loss forward once it's reached the configured
    # profit trigger -- never used to move it backward (the caller
    # is responsible for only calling this with a price that
    # improves the position's protection; see
    # PositionManagerAgent._apply_breakeven for the actual
    # monotonic-only check).

    def update_stop_loss(
        self,
        trade_id: int,
        new_stop_loss: float,
        mark_breakeven_applied: bool = False,
        new_order_list_id: str | None = None
    ):

        if not self._is_valid_price(
            new_stop_loss
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

            managed_trade.stop_loss = (
                new_stop_loss
            )

            if mark_breakeven_applied:

                managed_trade.breakeven_enabled = (
                    True
                )

            # LIVE only: the OCO that previously protected this
            # trade was canceled and replaced with a new one (a
            # single resting order pair can't have one leg moved in
            # place -- see PositionManagerAgent._apply_breakeven's
            # LIVE path). This new id must replace the stale one in
            # the SAME transaction as the stop_loss move, or a crash
            # between the two writes could leave the local record
            # pointing at an order_list_id that no longer exists.
            if new_order_list_id is not None:

                managed_trade.order_list_id = (
                    new_order_list_id
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
    # UPDATE TAKE PROFIT
    # =====================================================
    #
    # Used by PositionManagerAgent's dynamic take-profit logic to
    # extend a position's take_profit forward once price approaches
    # the original target during a strong favorable trend -- never
    # used to move it backward (the caller is responsible for only
    # calling this with a price that extends, not shrinks, the
    # target; see PositionManagerAgent._apply_dynamic_take_profit).

    def update_take_profit(
        self,
        trade_id: int,
        new_take_profit: float,
        mark_take_profit_extended: bool = False,
        new_order_list_id: str | None = None
    ):

        if not self._is_valid_price(
            new_take_profit
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

            managed_trade.take_profit = (
                new_take_profit
            )

            if mark_take_profit_extended:

                managed_trade.take_profit_extended = (
                    True
                )

            # LIVE only: see update_stop_loss's new_order_list_id
            # for the full reasoning -- the previous OCO was
            # canceled and replaced as a unit, so its new id needs
            # to land in the same transaction as the take_profit
            # move.
            if new_order_list_id is not None:

                managed_trade.order_list_id = (
                    new_order_list_id
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
        self,
        user_id: int
    ):

        """
        Deletes only this user's trades. user_id is required and
        deliberately has no default -- backtest/optimizer code uses
        a dedicated sandbox id (999) specifically so this can never
        be confused with a real account's history (0 in this
        project), but only if every caller actually passes it.

        Bug fixed: this previously deleted EVERY row in the trades
        table, for every user, with no filter at all. Both
        backtest/runner.py and backtest/optimizer/optimizer_engine.py
        called this once per run/combination to clear their own
        sandbox (user_id=999) trades before each backtest pass, but
        it silently wiped real paper-trading history (user_id=0)
        along with it every single time either was run.
        """

        session = self._session()

        try:

            session.query(
                Trade
            ).filter(
                Trade.user_id == user_id
            ).delete()

            session.commit()

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def reset_all(
        self
    ):

        """
        Deletes every trade for every user. Test-only: the isolated
        test database (see tests/conftest.py) is truncated between
        tests via this method specifically so it can never be
        confused with -- or accidentally substituted for -- the
        user_id-scoped reset() above, which is the one any real
        code path should ever call.
        """

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
