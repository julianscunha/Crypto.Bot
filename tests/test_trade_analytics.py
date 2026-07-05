# -*- coding: utf-8 -*-

"""
Unit tests for core/services/trade_analytics.py

These are pure functions (no DB), extracted from
backtest/engine/metrics_engine.py so the live trade_metrics_service
and the backtest engine compute equity-curve/streak/risk-adjusted
numbers via one shared implementation instead of two separate ones
that could silently drift apart.
"""

from core.services.trade_analytics import (
    compute_equity_curve_stats,
    compute_profit_factor,
    compute_risk_reward,
    compute_recovery_factor,
    compute_sharpe_ratio,
    compute_sortino_ratio
)


class TestComputeEquityCurveStats:

    def test_empty_list(self):

        result = compute_equity_curve_stats([])

        assert result["final_equity"] == 0.0

        assert result["max_drawdown"] == 0.0

        assert result["max_win_streak"] == 0

        assert result["max_loss_streak"] == 0

    def test_all_wins_no_drawdown(self):

        result = compute_equity_curve_stats(
            [10, 10, 10]
        )

        assert result["final_equity"] == 30.0

        assert result["max_drawdown"] == 0.0

        assert result["max_win_streak"] == 3

        assert result["max_loss_streak"] == 0

        assert result["current_win_streak"] == 3

    def test_all_losses(self):

        result = compute_equity_curve_stats(
            [-5, -5, -5]
        )

        assert result["final_equity"] == -15.0

        assert result["max_drawdown"] == -15.0

        assert result["max_win_streak"] == 0

        assert result["max_loss_streak"] == 3

        assert result["current_loss_streak"] == 3

    def test_known_sequence_drawdown(self):

        # equity path: 10, 20, 15, 25, 20, 15, 10
        # peak path:   10, 20, 20, 25, 25, 25, 25
        # drawdown:     0,  0, -5,  0, -5,-10,-15
        result = compute_equity_curve_stats(
            [10, 10, -5, 10, -5, -5, -5]
        )

        assert result["max_drawdown"] == -15.0

        assert result["max_win_streak"] == 2

        assert result["max_loss_streak"] == 3

    def test_streak_resets_on_alternation(self):

        result = compute_equity_curve_stats(
            [10, -5, 10, -5, 10]
        )

        assert result["max_win_streak"] == 1

        assert result["max_loss_streak"] == 1

        # most recent trade was a win
        assert result["current_win_streak"] == 1

        assert result["current_loss_streak"] == 0

    def test_current_streak_reflects_most_recent_trades_only(self):

        result = compute_equity_curve_stats(
            [10, 10, -5, -5, -5]
        )

        # the sequence ends on 3 losses; current_loss_streak must
        # reflect that even though an earlier win streak was longer
        # in absolute count
        assert result["current_loss_streak"] == 3

        assert result["current_win_streak"] == 0

    def test_zero_pnl_trade_counts_as_loss_bucket(self):

        # a breakeven trade (pnl == 0) is not a win (pnl > 0 is the
        # only win condition); it must not silently vanish from
        # both streak counters
        result = compute_equity_curve_stats(
            [10, 0, 10]
        )

        assert len(result["wins"]) == 2

        assert len(result["losses"]) == 1

        assert result["losses"][0] == 0


class TestComputeProfitFactor:

    def test_typical_case(self):

        assert compute_profit_factor(
            [10, 10, 10],
            [5, 5, 5, 5]
        ) == 1.5

    def test_no_losses_returns_zero(self):

        # avoids division by zero; matches the existing backtest
        # engine convention of returning 0 rather than infinity
        assert compute_profit_factor(
            [10, 10],
            []
        ) == 0.0

    def test_no_wins(self):

        assert compute_profit_factor(
            [],
            [5, 5]
        ) == 0.0


class TestComputeRiskReward:

    def test_typical_case(self):

        # avg_win=10, avg_loss=5 -> 2.0
        assert compute_risk_reward(
            [10, 10],
            [5, 5]
        ) == 2.0

    def test_no_losses_returns_zero(self):

        assert compute_risk_reward(
            [10, 10],
            []
        ) == 0.0


class TestComputeRecoveryFactor:

    def test_typical_case(self):

        assert compute_recovery_factor(
            100.0,
            -25.0
        ) == 4.0

    def test_zero_drawdown_returns_raw_pnl(self):

        assert compute_recovery_factor(
            50.0,
            0.0
        ) == 50.0


class TestComputeSharpeRatio:

    def test_returns_zero_for_fewer_than_two_trades(self):

        assert compute_sharpe_ratio([10]) == 0.0

        assert compute_sharpe_ratio([]) == 0.0

    def test_returns_zero_for_constant_returns(self):

        # zero standard deviation -- must not divide by zero
        assert compute_sharpe_ratio([10, 10, 10]) == 0.0

    def test_positive_for_consistently_profitable_trades(self):

        result = compute_sharpe_ratio(
            [10, 12, 9, 11, 10]
        )

        assert result > 0

    def test_negative_for_consistently_losing_trades(self):

        result = compute_sharpe_ratio(
            [-10, -12, -9, -11, -10]
        )

        assert result < 0


class TestComputeSortinoRatio:

    def test_returns_zero_for_fewer_than_two_trades(self):

        assert compute_sortino_ratio([10]) == 0.0

    def test_returns_zero_when_no_losing_trades(self):

        # no downside deviation to divide by -- treated as 0.0,
        # not an undefined/infinite ratio
        assert compute_sortino_ratio(
            [10, 10, 10]
        ) == 0.0

    def test_positive_for_a_profitable_mixed_sequence(self):

        result = compute_sortino_ratio(
            [10, 12, -3, 11, 10]
        )

        assert result > 0

    def test_only_penalizes_downside_not_upside_volatility(self):

        # same mean, but one sequence has a big upside outlier and
        # the other a big downside outlier -- Sortino must penalize
        # the downside case much more heavily, unlike Sharpe which
        # would penalize both
        upside_outlier = [5, 5, 5, 35]

        downside_outlier = [5, 5, 5, -25]

        sortino_upside = compute_sortino_ratio(
            upside_outlier
        )

        sortino_downside = compute_sortino_ratio(
            downside_outlier
        )

        assert sortino_upside > sortino_downside
