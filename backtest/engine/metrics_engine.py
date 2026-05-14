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

        wins = []

        losses = []

        current_win_streak = 0

        current_loss_streak = 0

        max_win_streak = 0

        max_loss_streak = 0

        # =====================================================
        # EQUITY + STREAKS
        # =====================================================

        for trade in trades:

            equity += trade.pnl

            if equity > peak:

                peak = equity

            drawdown = (
                equity - peak
            )

            if drawdown < max_drawdown:

                max_drawdown = drawdown

            # =============================================
            # WIN / LOSS ANALYTICS
            # =============================================

            if trade.pnl > 0:

                wins.append(
                    trade.pnl
                )

                current_win_streak += 1

                current_loss_streak = 0

                if (
                    current_win_streak
                    > max_win_streak
                ):

                    max_win_streak = (
                        current_win_streak
                    )

            else:

                losses.append(
                    abs(trade.pnl)
                )

                current_loss_streak += 1

                current_win_streak = 0

                if (
                    current_loss_streak
                    > max_loss_streak
                ):

                    max_loss_streak = (
                        current_loss_streak
                    )

        # =====================================================
        # QUANT METRICS
        # =====================================================

        gross_profit = (
            sum(wins)
        )

        gross_loss = (
            sum(losses)
        )

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else 0
        )

        avg_win = (
            gross_profit / len(wins)
            if len(wins) > 0
            else 0
        )
        
        avg_loss = (
            gross_loss / len(losses)
            if len(losses) > 0
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
            avg_win / avg_loss
            if avg_loss > 0
            else 0
        )

        pnl = (
            metrics["pnl"]
        )

        recovery_factor = (
            pnl / abs(max_drawdown)
            if max_drawdown != 0
            else pnl
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