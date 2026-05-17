# -*- coding: utf-8 -*-

from sqlalchemy.orm import (
    Session
)

from sqlalchemy import (
    func
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    Trade
)


class MetricsStorage:

    # =====================================================
    # SESSION
    # =====================================================

    def _session(
        self
    ) -> Session:

        return SessionLocal()

    # =====================================================
    # METRICS
    # =====================================================

    def get_metrics(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            trades = (

                session.query(Trade)

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "CLOSED"
                )

                .all()
            )

            total_trades = len(
                trades
            )

            # =================================================
            # EMPTY
            # =================================================

            if total_trades == 0:

                return {

                    "total_trades": 0,

                    "winning_trades": 0,

                    "losing_trades": 0,

                    "winrate": 0.0,

                    "pnl": 0.0
                }

            # =================================================
            # WINNERS
            # =================================================

            winning_trades = len(

                [

                    trade

                    for trade in trades

                    if (
                        trade.pnl or 0.0
                    ) > 0
                ]
            )

            # =================================================
            # LOSERS
            # =================================================

            losing_trades = len(

                [

                    trade

                    for trade in trades

                    if (
                        trade.pnl or 0.0
                    ) < 0
                ]
            )

            # =================================================
            # TOTAL PNL
            # =================================================

            total_pnl = round(

                sum(

                    trade.pnl or 0.0

                    for trade in trades
                ),

                2
            )

            # =================================================
            # WINRATE
            # =================================================

            winrate = round(

                (
                    winning_trades
                    / total_trades
                ) * 100,

                2
            )

            return {

                "total_trades":
                    total_trades,

                "winning_trades":
                    winning_trades,

                "losing_trades":
                    losing_trades,

                "winrate":
                    winrate,

                "pnl":
                    total_pnl
            }

        finally:

            session.close()

    # =====================================================
    # OPEN EXPOSURE
    # =====================================================

    def total_open_exposure(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            result = (

                session.query(

                    func.sum(

                        Trade.current_price
                        *
                        Trade.quantity
                    )
                )

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "OPEN"
                )

                .scalar()
            )

            if result is None:

                return 0.0

            return round(
                result,
                2
            )

        finally:

            session.close()