# -*- coding: utf-8 -*-

from sqlalchemy.orm import (
    Session
)

from sqlalchemy import (
    desc,
    func
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    PortfolioSnapshot
)


class PortfolioRepository:

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
    def _safe_positive_float(
        value: float
    ) -> float:

        return round(

            max(
                float(value or 0.0),
                0.0
            ),

            2
        )

    @staticmethod
    def _safe_float(
        value: float
    ) -> float:

        return round(
            float(value or 0.0),
            2
        )

    @staticmethod
    def _safe_positive_int(
        value: int
    ) -> int:

        return max(
            int(value or 0),
            0
        )

    # =====================================================
    # CREATE SNAPSHOT
    # =====================================================

    def create_snapshot(
        self,
        user_id: int,
        balance: float,
        equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
        total_pnl: float,
        open_positions: int,
        closed_positions: int,
        exposure: float,
        drawdown: float,
        initial_balance: float = 0.0
    ):

        session = self._session()

        try:

            portfolio_snapshot = (

                PortfolioSnapshot(

                    user_id=user_id,

                    balance=self._safe_positive_float(
                        balance
                    ),

                    equity=self._safe_positive_float(
                        equity
                    ),

                    realized_pnl=self._safe_float(
                        realized_pnl
                    ),

                    unrealized_pnl=self._safe_float(
                        unrealized_pnl
                    ),

                    total_pnl=self._safe_float(
                        total_pnl
                    ),

                    open_positions=self._safe_positive_int(
                        open_positions
                    ),

                    closed_positions=self._safe_positive_int(
                        closed_positions
                    ),

                    exposure=self._safe_positive_float(
                        exposure
                    ),

                    drawdown=self._safe_positive_float(
                        drawdown
                    ),

                    initial_balance=self._safe_positive_float(
                        initial_balance
                    )
                )
            )

            session.add(
                portfolio_snapshot
            )

            session.commit()

            session.refresh(
                portfolio_snapshot
            )

            return portfolio_snapshot

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    # =====================================================
    # GET SNAPSHOT
    # =====================================================

    def get_snapshot(
        self,
        snapshot_id: int
    ):

        session = self._session()

        try:

            return (

                session.query(
                    PortfolioSnapshot
                )

                .filter(
                    PortfolioSnapshot.id
                    == snapshot_id
                )

                .first()
            )

        finally:

            session.close()

    # =====================================================
    # GET LATEST SNAPSHOT
    # =====================================================

    def get_latest_snapshot(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            return (

                session.query(
                    PortfolioSnapshot
                )

                .filter(
                    PortfolioSnapshot.user_id
                    == user_id
                )

                .order_by(
                    desc(
                        PortfolioSnapshot.id
                    )
                )

                .first()
            )

        finally:

            session.close()

    # =====================================================
    # GET SNAPSHOT HISTORY
    # =====================================================

    def get_snapshot_history(
        self,
        user_id: int,
        limit: int = 100
    ):

        session = self._session()

        try:

            limit = max(
                int(limit or 1),
                1
            )

            return (

                session.query(
                    PortfolioSnapshot
                )

                .filter(
                    PortfolioSnapshot.user_id
                    == user_id
                )

                .order_by(
                    desc(
                        PortfolioSnapshot.id
                    )
                )

                .limit(limit)

                .all()
            )

        finally:

            session.close()

    # =====================================================
    # GET MAX EQUITY (HISTORICAL PEAK)
    # =====================================================

    def get_max_equity(
        self,
        user_id: int,
        initial_balance: float | None = None
    ) -> float:

        session = self._session()

        try:

            query = (

                session.query(
                    func.max(
                        PortfolioSnapshot.equity
                    )
                )

                .filter(
                    PortfolioSnapshot.user_id
                    == user_id
                )
            )

            # =================================================
            # SESSION SCOPING
            # =================================================
            #
            # Without this filter, a deliberate paper-account reset
            # (e.g. account_balance going from 100 to 10 in
            # core/config/trading_config.py) leaves old, much higher
            # equity snapshots in the table. Those would otherwise
            # count as "historical peak" forever, turning a config
            # change into what looks like a 90% real trading loss.
            # Scoping to snapshots created under the SAME configured
            # initial_balance keeps drawdown meaningful across resets.
            #
            # initial_balance=None (the default for backward
            # compatibility with direct callers/older snapshots
            # that predate this column) means "don't scope" --
            # existing behavior is preserved for those callers.

            if initial_balance is not None:

                query = query.filter(
                    PortfolioSnapshot.initial_balance
                    == round(
                        float(initial_balance),
                        2
                    )
                )

            result = query.scalar()

            return float(
                result or 0.0
            )

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
        Deletes only this user's portfolio snapshots. See
        TradesRepository.reset() for why user_id is required here
        too -- the same unscoped-delete bug existed in this method.
        """

        session = self._session()

        try:

            session.query(
                PortfolioSnapshot
            ).filter(
                PortfolioSnapshot.user_id == user_id
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
        Deletes every portfolio snapshot for every user. Test-only:
        the isolated test database (see tests/conftest.py) is
        truncated between tests via this method specifically so it
        can never be confused with -- or accidentally substituted
        for -- the user_id-scoped reset() above, which is the one
        any real code path should ever call.
        """

        session = self._session()

        try:

            session.query(
                PortfolioSnapshot
            ).delete()

            session.commit()

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()


portfolio_repository = (
    PortfolioRepository()
)
