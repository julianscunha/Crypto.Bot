# -*- coding: utf-8 -*-

"""
Unit tests for data/features/indicators.py

This module's atr() function is actively used by
core/agents/strategy_agent.py for live stop-loss/take-profit sizing,
so its correctness matters even though it's a simpler close-to-close
approximation rather than the high/low/close true-range engine in
core/services/atr_service.py.
"""

from data.features.indicators import (
    ema,
    rsi,
    atr,
    safe_float,
    validate_period,
    validate_series
)


class TestSafeFloat:

    def test_converts_valid_number(self):

        assert safe_float("10.5") == 10.5

    def test_returns_fallback_on_invalid_input(self):

        assert safe_float("not_a_number", fallback=-1.0) == -1.0

    def test_default_fallback_is_zero(self):

        assert safe_float(None) == 0.0


class TestValidatePeriod:

    def test_positive_int_is_valid(self):

        assert validate_period(14) is True

    def test_zero_is_invalid(self):

        assert validate_period(0) is False

    def test_negative_is_invalid(self):

        assert validate_period(-5) is False

    def test_non_numeric_is_invalid(self):

        assert validate_period("abc") is False


class TestValidateSeries:

    def test_empty_series_is_invalid(self):

        assert validate_series([]) is False

    def test_series_shorter_than_minimum_is_invalid(self):

        assert validate_series([1, 2], minimum_length=5) is False

    def test_series_meeting_minimum_is_valid(self):

        assert validate_series([1, 2, 3], minimum_length=3) is True


class TestEma:

    def test_returns_none_for_insufficient_data(self):

        assert ema([1.0, 2.0], period=10) is None

    def test_returns_none_for_invalid_period(self):

        assert ema([1.0, 2.0, 3.0], period=0) is None

    def test_simple_average_with_exact_period(self):

        result = ema(
            [10.0, 20.0, 30.0],
            period=3
        )

        assert result == 20.0

    def test_uses_default_period_when_none_given(self):

        # default_ema_period comes from INDICATORS_CONFIG; as long as
        # this doesn't raise and returns a sane value with plenty of
        # data, the default-period path is exercised
        values = [float(100 + i) for i in range(50)]

        result = ema(values)

        assert result is not None

        assert result > 0

    def test_reacts_to_upward_trend(self):

        rising = [float(100 + i) for i in range(20)]

        result = ema(rising, period=10)

        assert result is not None

        assert result < rising[-1]

        assert result > rising[0]


class TestRsi:

    def test_returns_none_for_insufficient_data(self):

        assert rsi([1.0, 2.0], period=14) is None

    def test_returns_none_for_invalid_period(self):

        assert rsi(
            [float(i) for i in range(20)],
            period=-1
        ) is None

    def test_returns_near_100_for_all_gains(self):

        # strictly increasing series -> no losses -> avg_loss falls
        # back to a tiny epsilon (not exactly 0), so RSI approaches
        # but does not necessarily hit exactly 100.0
        values = [float(100 + i) for i in range(20)]

        result = rsi(values, period=14)

        assert result is not None

        assert result > 99.0

    def test_returns_low_value_for_all_losses(self):

        # strictly decreasing series -> no gains -> RSI near 0
        values = [float(120 - i) for i in range(20)]

        result = rsi(values, period=14)

        assert result is not None

        assert result < 10.0

    def test_returns_mid_range_for_choppy_series(self):

        values = [
            100, 102, 99, 103, 98, 104, 97, 105, 96, 106,
            95, 107, 94, 108, 93, 109
        ]

        result = rsi(
            [float(v) for v in values],
            period=14
        )

        assert result is not None

        assert 0.0 <= result <= 100.0


class TestAtr:

    def test_returns_none_for_insufficient_data(self):

        assert atr([1.0, 2.0], period=14) is None

    def test_returns_none_for_invalid_period(self):

        assert atr(
            [float(i) for i in range(20)],
            period=0
        ) is None

    def test_returns_positive_value_for_volatile_series(self):

        values = [
            100.0, 105.0, 98.0, 107.0, 95.0,
            110.0, 92.0, 112.0, 90.0, 115.0,
            88.0, 117.0, 86.0, 119.0, 84.0
        ]

        result = atr(values, period=14)

        assert result is not None

        assert result > 0

    def test_returns_near_zero_for_flat_series(self):

        values = [100.0] * 20

        result = atr(values, period=14)

        assert result == 0.0

    def test_uses_default_period_when_none_given(self):

        values = [float(100 + (i % 5)) for i in range(30)]

        result = atr(values)

        assert result is not None
