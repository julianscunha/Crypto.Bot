# -*- coding: utf-8 -*-

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
        drawdown: float
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
    # RESET
    # =====================================================

    def reset(
        self
    ):

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