# -*- coding: utf-8 -*-

from sqlalchemy.orm import (
    Session
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    PortfolioSnapshot
)


class PortfolioRepository:

    # =====================================================
    # SESSION
    # =====================================================

    def _session(
        self
    ) -> Session:

        return SessionLocal()

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

        # =================================================
        # SAFETY
        # =================================================

        balance = round(
            max(balance, 0.0),
            2
        )

        equity = round(
            max(equity, 0.0),
            2
        )

        realized_pnl = round(
            realized_pnl,
            2
        )

        unrealized_pnl = round(
            unrealized_pnl,
            2
        )

        total_pnl = round(
            total_pnl,
            2
        )

        exposure = round(
            max(exposure, 0.0),
            2
        )

        drawdown = round(
            max(drawdown, 0.0),
            2
        )

        session = self._session()

        try:

            snapshot = (
                PortfolioSnapshot(

                    user_id=user_id,

                    balance=balance,

                    equity=equity,

                    realized_pnl=realized_pnl,

                    unrealized_pnl=unrealized_pnl,

                    total_pnl=total_pnl,

                    open_positions=max(
                        open_positions,
                        0
                    ),

                    closed_positions=max(
                        closed_positions,
                        0
                    ),

                    exposure=exposure,

                    drawdown=drawdown
                )
            )

            session.add(
                snapshot
            )

            session.commit()

            session.refresh(
                snapshot
            )

            return snapshot

        except Exception:

            session.rollback()

            raise

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
                    PortfolioSnapshot.id.desc()
                )

                .first()
            )

        finally:

            session.close()