# -*- coding: utf-8 -*-

from data.storage.metrics import (
    MetricsStorage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


class MetricsEngine:

    def __init__(self):

        self.metrics = (
            MetricsStorage()
        )

    def generate(
        self,
        user_id: int
    ):

        metrics = (
            self.metrics.get_metrics(
                user_id=user_id
            )
        )

        trades = (
            trades_repository.get_closed_trades(
                user_id=user_id
            )
        )

        equity = 0

        peak = 0

        max_drawdown = 0

        for trade in trades:

            equity += trade.pnl

            if equity > peak:
                peak = equity

            drawdown = (
                equity - peak
            )

            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return {

            "total_trades":
                metrics["total_trades"],

            "winrate":
                metrics["winrate"],

            "pnl":
                metrics["pnl"],

            "max_drawdown":
                round(
                    max_drawdown,
                    2
                )
        }