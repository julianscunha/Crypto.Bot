# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal
from data.storage.models import EquityCurve


class EquityRepository:

    def __init__(self):

        self.db: Session = SessionLocal()

    def save_snapshot(
        self,
        user_id: int,
        equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
        drawdown: float
    ):

        row = EquityCurve(
            user_id=user_id,
            equity=equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            drawdown=drawdown
        )

        self.db.add(row)

        self.db.commit()

    def get_latest(
        self,
        user_id: int
    ):

        return (
            self.db.query(EquityCurve)
            .filter(
                EquityCurve.user_id == user_id
            )
            .order_by(EquityCurve.id.desc())
            .first()
        )