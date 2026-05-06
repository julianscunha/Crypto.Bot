# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal

from data.storage.models import PortfolioSnapshot


class PortfolioRepository:

    def _session(self) -> Session:

        return SessionLocal()

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

            snapshot = PortfolioSnapshot(
                user_id=user_id,
                balance=balance,
                equity=equity,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                total_pnl=total_pnl,
                open_positions=open_positions,
                closed_positions=closed_positions,
                exposure=exposure,
                drawdown=drawdown
            )

            session.add(snapshot)

            session.commit()

            session.refresh(snapshot)

            return snapshot

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def get_latest_snapshot(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            return (
                session.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.user_id == user_id
                )
                .order_by(
                    PortfolioSnapshot.id.desc()
                )
                .first()
            )

        finally:

            session.close()
