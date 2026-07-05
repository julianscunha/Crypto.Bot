# -*- coding: utf-8 -*-

"""
Unit tests for core/services/ema_trend_service.py
"""

from core.services.ema_trend_service import (
    EmaTrendService
)


class TestUpdatePrice:

    def test_adds_valid_price(self):

        service = EmaTrendService()

        service.update_price(1, "BTCUSDT", 100.0)

        assert service.get_prices(1, "BTCUSDT") == [100.0]

    def test_rejects_zero_or_negative(self):

        service = EmaTrendService()

        service.update_price(1, "BTCUSDT", 0.0)

        service.update_price(1, "BTCUSDT", -10.0)

        assert service.get_prices(1, "BTCUSDT") == []

    def test_respects_max_history(self):

        service = EmaTrendService()

        service.max_history = 5

        for price in range(10):

            service.update_price(1, "BTCUSDT", float(price + 1))

        prices = service.get_prices(1, "BTCUSDT")

        assert len(prices) == 5


class TestCalculateEma:

    def test_returns_none_for_empty_prices(self):

        service = EmaTrendService()

        assert service.calculate_ema([], period=5) is None

    def test_returns_none_for_insufficient_prices(self):

        service = EmaTrendService()

        assert service.calculate_ema(
            [1.0, 2.0, 3.0],
            period=5
        ) is None

    def test_returns_none_for_zero_period(self):

        service = EmaTrendService()

        assert service.calculate_ema(
            [1.0, 2.0, 3.0],
            period=0
        ) is None

    def test_simple_moving_average_with_exact_period(self):

        service = EmaTrendService()

        # with exactly `period` prices, EMA == SMA of those prices
        ema = service.calculate_ema(
            [10.0, 20.0, 30.0],
            period=3
        )

        assert ema == 20.0

    def test_ema_reacts_to_trend(self):

        service = EmaTrendService()

        rising_prices = [
            float(p) for p in range(100, 130)
        ]

        ema = service.calculate_ema(
            rising_prices,
            period=10
        )

        # EMA of a rising series should sit below the latest price
        # but above the earliest prices
        assert ema is not None

        assert ema < rising_prices[-1]

        assert ema > rising_prices[0]


class TestCalculateEmaSpreadPercent:

    def test_returns_none_during_warmup(self):

        service = EmaTrendService()

        service.update_price(1, "BTCUSDT", 100.0)

        spread = service.calculate_ema_spread_percent(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        )

        assert spread is None

    def test_positive_spread_in_uptrend(self):

        service = EmaTrendService()

        price = 100.0

        for _ in range(30):

            service.update_price(1, "BTCUSDT", price)

            price += 1.0

        spread = service.calculate_ema_spread_percent(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        )

        assert spread is not None

        # fast EMA should be above slow EMA in a clean uptrend
        assert spread > 0

    def test_negative_spread_in_downtrend(self):

        service = EmaTrendService()

        price = 200.0

        for _ in range(30):

            service.update_price(1, "BTCUSDT", price)

            price -= 1.0

        spread = service.calculate_ema_spread_percent(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        )

        assert spread is not None

        assert spread < 0


class TestIsBullish:

    def test_false_during_warmup(self):

        service = EmaTrendService()

        assert service.is_bullish(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        ) is False

    def test_true_in_strong_uptrend(self):

        service = EmaTrendService()

        price = 100.0

        for _ in range(30):

            service.update_price(1, "BTCUSDT", price)

            price += 2.0

        assert service.is_bullish(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        ) is True

    def test_false_in_downtrend(self):

        service = EmaTrendService()

        price = 200.0

        for _ in range(30):

            service.update_price(1, "BTCUSDT", price)

            price -= 2.0

        assert service.is_bullish(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        ) is False


class TestGetTrendStrength:

    def test_zero_during_warmup(self):

        service = EmaTrendService()

        strength = service.get_trend_strength(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        )

        assert strength == 0.0

    def test_positive_strength_with_trend(self):

        service = EmaTrendService()

        price = 100.0

        for _ in range(30):

            service.update_price(1, "BTCUSDT", price)

            price += 2.0

        strength = service.get_trend_strength(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        )

        assert strength > 0

    def test_strength_is_always_non_negative(self):

        service = EmaTrendService()

        price = 200.0

        for _ in range(30):

            service.update_price(1, "BTCUSDT", price)

            price -= 2.0

        strength = service.get_trend_strength(
            user_id=1,
            symbol="BTCUSDT",
            fast_period=5,
            slow_period=20
        )

        # strength is abs(spread); even in a downtrend it must be >= 0
        assert strength >= 0


class TestReset:

    def test_reset_clears_history(self):

        service = EmaTrendService()

        service.update_price(1, "BTCUSDT", 100.0)

        service.reset()

        assert service.get_prices(1, "BTCUSDT") == []
