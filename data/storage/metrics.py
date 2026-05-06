# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session
from sqlalchemy import func

from data.storage.database import SessionLocal
from data.storage.models import Trade


class MetricsStorage:

    def __init__(self):

        self.db: Session = SessionLocal()

    def get_metrics(
        self,
        user_id: int
    ):

        trades = (
            self.db.query(Trade)
            .filter(
                Trade.user_id == user_id,
                Trade.status == "CLOSED"
            )
            .all()
        )

        total_trades = len(trades)

        if total_trades == 0:

            return {
                "total_trades": 0,
                "winrate": 0,
                "pnl": 0
            }

        wins = len([
            t for t in trades
            if t.pnl > 0
        ])

        total_pnl = sum([
            t.pnl for t in trades
        ])

        return {
            "total_trades": total_trades,
            "winrate": round(wins / total_trades, 2),
            "pnl": round(total_pnl, 2)
        }

    def total_open_exposure(
        self,
        user_id: int
    ):

        result = (
            self.db.query(
                func.sum(
                    Trade.current_price * Trade.quantity
                )
            )
            .filter(
                Trade.user_id == user_id,
                Trade.status == "OPEN"
            )
            .scalar()
        )

        return result or 0