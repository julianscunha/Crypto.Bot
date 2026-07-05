# -*- coding: utf-8 -*-

from data.storage.metrics import (
    MetricsStorage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.services.trade_analytics import (
    compute_equity_curve_stats,
    compute_profit_factor,
    compute_risk_reward,
    compute_recovery_factor
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

        # =====================================================
        # EQUITY + STREAKS
        # =====================================================
        #
        # get_closed_trades() orders by closed_at DESC; the equity
        # curve must walk forward in time, oldest trade first.

        pnls = [
            trade.pnl
            for trade in reversed(trades)
        ]

        curve_stats = (
            compute_equity_curve_stats(
                pnls
            )
        )

        max_drawdown = (
            curve_stats["max_drawdown"]
        )

        wins = (
            curve_stats["wins"]
        )

        losses = (
            curve_stats["losses"]
        )

        max_win_streak = (
            curve_stats["max_win_streak"]
        )

        max_loss_streak = (
            curve_stats["max_loss_streak"]
        )

        # =====================================================
        # QUANT METRICS
        # =====================================================

        profit_factor = (
            compute_profit_factor(
                wins,
                losses
            )
        )

        avg_win = (
            sum(wins) / len(wins)
            if wins
            else 0
        )

        avg_loss = (
            sum(losses) / len(losses)
            if losses
            else 0
        )

        winrate = (
            metrics["winrate"]
        )

        expectancy = (
            (
                avg_win * winrate
            )
            -
            (
                avg_loss * (
                    1 - winrate
                )
            )
        )

        risk_reward = (
            compute_risk_reward(
                wins,
                losses
            )
        )

        pnl = (
            metrics["pnl"]
        )

        recovery_factor = (
            compute_recovery_factor(
                pnl,
                max_drawdown
            )
        )

        # =====================================================
        # RETURN
        # =====================================================

        return {

            "total_trades":
                metrics["total_trades"],

            "winrate":
                round(
                    winrate,
                    2
                ),

            "pnl":
                round(
                    pnl,
                    2
                ),

            "max_drawdown":
                round(
                    max_drawdown,
                    2
                ),

            "profit_factor":
                round(
                    profit_factor,
                    2
                ),

            "expectancy":
                round(
                    expectancy,
                    2
                ),

            "avg_win":
                round(
                    avg_win,
                    2
                ),

            "avg_loss":
                round(
                    avg_loss,
                    2
                ),

            "risk_reward":
                round(
                    risk_reward,
                    2
                ),

            "recovery_factor":
                round(
                    recovery_factor,
                    2
                ),

            "max_win_streak":
                max_win_streak,

            "max_loss_streak":
                max_loss_streak
        }
