# -*- coding: utf-8 -*-

"""
Thin storage-facing wrapper around TradeMetricsService.

backtest.engine.metrics_engine expects a `MetricsStorage` class exposing
`get_metrics(user_id=...)` with at least `total_trades`, `winrate`, and
`pnl` keys. The rest of the backtest/optimizer/report stack (see
backtest/reports/validation_interpreter.py and
backtest/optimizer/optimizer_engine.py) treats `winrate` as a 0-1
fraction (e.g. compared against 0.40 / 0.55, formatted with `:.2%`).

TradeMetricsService.get_metrics() returns winrate as a 0-100 percentage
(it's display-oriented, used directly by the API/dashboard). This class
re-exposes the same underlying metrics but normalizes winrate to a 0-1
fraction so every consumer of MetricsStorage shares one convention.
"""

from core.services.trade_metrics_service import (
    trade_metrics_service
)


class MetricsStorage:

    def __init__(
        self,
        service=None
    ):

        self.service = (
            service
            or trade_metrics_service
        )

    # =====================================================
    # METRICS
    # =====================================================

    def get_metrics(
        self,
        user_id: int
    ):

        metrics = (
            self.service.get_metrics(
                user_id=user_id
            )
        )

        # =================================================
        # NORMALIZE WINRATE: 0-100 -> 0-1
        # =================================================

        normalized = dict(
            metrics
        )

        normalized["winrate"] = round(
            (metrics["winrate"] or 0.0) / 100,
            4
        )

        return normalized
