# -*- coding: utf-8 -*-

from data.storage.metrics import (
    MetricsStorage
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

        return {

            "total_trades":
                metrics["total_trades"],

            "winrate":
                metrics["winrate"],

            "pnl":
                metrics["pnl"]
        }