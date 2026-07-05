# -*- coding: utf-8 -*-

"""
Pure, no-I/O analytics functions over a sequence of trade PnLs.

Extracted from backtest/engine/metrics_engine.py (which originally
computed equity curve, drawdown, and win/loss streaks only for
backtests) so the live trade_metrics_service can compute the exact
same numbers for real trading without re-implementing -- and
potentially drifting from -- the same logic in a second place.

Every function here takes a list of realized trade PnLs, in the
order the trades closed, and returns a plain value or dict. No
database, no user_id, no session handling -- callers (backtest's
MetricsEngine, core.services.trade_metrics_service.TradeMetricsService)
own fetching the trades and pass in just the numbers.
"""

import math


# =====================================================
# EQUITY CURVE + DRAWDOWN + STREAKS
# =====================================================

def compute_equity_curve_stats(
    pnls: list[float]
) -> dict:

    """
    Single pass over closed-trade PnLs (in close order) computing
    the running equity curve, max drawdown, and longest win/loss
    streaks -- exactly the loop backtest/engine/metrics_engine.py
    used to run on its own.

    max_drawdown is returned as a negative-or-zero number (the
    largest peak-to-trough dip in cumulative PnL), matching the
    existing backtest convention.
    """

    equity = 0.0

    peak = 0.0

    max_drawdown = 0.0

    wins = []

    losses = []

    current_win_streak = 0

    current_loss_streak = 0

    max_win_streak = 0

    max_loss_streak = 0

    for pnl in pnls:

        equity += pnl

        if equity > peak:

            peak = equity

        drawdown = (
            equity
            -
            peak
        )

        if drawdown < max_drawdown:

            max_drawdown = drawdown

        if pnl > 0:

            wins.append(pnl)

            current_win_streak += 1

            current_loss_streak = 0

            if current_win_streak > max_win_streak:

                max_win_streak = current_win_streak

        else:

            losses.append(
                abs(pnl)
            )

            current_loss_streak += 1

            current_win_streak = 0

            if current_loss_streak > max_loss_streak:

                max_loss_streak = current_loss_streak

    return {

        "final_equity":
            round(equity, 2),

        "max_drawdown":
            round(max_drawdown, 2),

        "wins":
            wins,

        "losses":
            losses,

        "max_win_streak":
            max_win_streak,

        "max_loss_streak":
            max_loss_streak,

        # streaks still open as of the most recent trade -- useful
        # for "how many losses in a row right now", distinct from
        # the all-time max_loss_streak
        "current_win_streak":
            current_win_streak,

        "current_loss_streak":
            current_loss_streak
    }


# =====================================================
# PROFIT FACTOR / EXPECTANCY / RISK-REWARD
# =====================================================

def compute_profit_factor(
    wins: list[float],
    losses: list[float]
) -> float:

    gross_profit = sum(wins)

    gross_loss = sum(losses)

    if gross_loss <= 0:

        return 0.0

    return round(
        gross_profit / gross_loss,
        2
    )


def compute_risk_reward(
    wins: list[float],
    losses: list[float]
) -> float:

    avg_win = (
        sum(wins) / len(wins)
        if wins
        else 0.0
    )

    avg_loss = (
        sum(losses) / len(losses)
        if losses
        else 0.0
    )

    if avg_loss <= 0:

        return 0.0

    return round(
        avg_win / avg_loss,
        2
    )


def compute_recovery_factor(
    total_pnl: float,
    max_drawdown: float
) -> float:

    if max_drawdown == 0:

        return round(total_pnl, 2)

    return round(
        total_pnl / abs(max_drawdown),
        2
    )


# =====================================================
# RISK-ADJUSTED RETURN (SHARPE / SORTINO)
# =====================================================
#
# These treat each trade's PnL as one "return" observation -- there
# is no natural per-trade "risk-free rate" for an intraday paper
# bot, so both ratios use the simplified, risk-free-rate-free form
# common in retail trading-strategy evaluation: mean return divided
# by (downside) deviation of returns. This is the standard
# adaptation used when evaluating a trade sequence rather than a
# periodic (daily/monthly) return series -- it is not a substitute
# for instrument-level risk-free benchmarking, only a way to compare
# this bot's own trade-to-trade consistency over time.

def _stdev(
    values: list[float]
) -> float:

    if len(values) < 2:

        return 0.0

    mean = sum(values) / len(values)

    variance = (

        sum(
            (value - mean) ** 2
            for value in values
        )

        /
        (len(values) - 1)
    )

    return math.sqrt(variance)


def compute_sharpe_ratio(
    pnls: list[float]
) -> float:

    if len(pnls) < 2:

        return 0.0

    mean_pnl = sum(pnls) / len(pnls)

    stdev_pnl = _stdev(pnls)

    if stdev_pnl == 0:

        return 0.0

    return round(
        mean_pnl / stdev_pnl,
        2
    )


def compute_sortino_ratio(
    pnls: list[float]
) -> float:

    if len(pnls) < 2:

        return 0.0

    mean_pnl = sum(pnls) / len(pnls)

    downside_pnls = [
        pnl
        for pnl in pnls
        if pnl < 0
    ]

    if not downside_pnls:

        # no losing trades at all -- conventionally treated as
        # "no downside risk observed", not as an undefined/infinite
        # ratio, since dividing by a zero downside deviation would
        # be meaningless rather than meaningfully "infinitely good"
        return 0.0

    downside_deviation = math.sqrt(

        sum(
            pnl ** 2
            for pnl in downside_pnls
        )

        /
        len(pnls)
    )

    if downside_deviation == 0:

        return 0.0

    return round(
        mean_pnl / downside_deviation,
        2
    )
