# -*- coding: utf-8 -*-

"""
Unit tests for core/services/atr_service.py
"""

from core.services.atr_service import (
    AtrService
)


class TestUpdateCandle:

    def test_adds_valid_candle(self):

        service = AtrService()

        service.update_candle(
            user_id=1,
            symbol="BTCUSDT",
            high=105.0,
            low=95.0,
            close=100.0
        )

        candles = service.get_candles(
            user_id=1,
            symbol="BTCUSDT"
        )

        assert len(candles) == 1

    def test_rejects_zero_high(self):

        service = AtrService()

        service.update_candle(
            user_id=1,
            symbol="BTCUSDT",
            high=0.0,
            low=95.0,
            close=100.0
        )

        assert service.get_candles(1, "BTCUSDT") == []

    def test_rejects_negative_low(self):

        service = AtrService()

        service.update_candle(
            user_id=1,
            symbol="BTCUSDT",
            high=105.0,
            low=-5.0,
            close=100.0
        )

        assert service.get_candles(1, "BTCUSDT") == []

    def test_rejects_low_greater_than_high(self):

        service = AtrService()

        service.update_candle(
            user_id=1,
            symbol="BTCUSDT",
            high=90.0,
            low=95.0,
            close=92.0
        )

        assert service.get_candles(1, "BTCUSDT") == []

    def test_respects_max_candle_history(self):

        service = AtrService()

        service.max_candles = 5

        for i in range(10):

            service.update_candle(
                user_id=1,
                symbol="BTCUSDT",
                high=100.0 + i,
                low=90.0 + i,
                close=95.0 + i
            )

        candles = service.get_candles(1, "BTCUSDT")

        assert len(candles) == 5

        # oldest candles should have been dropped, newest retained
        assert candles[-1]["close"] == 95.0 + 9


class TestCalculateTrueRange:

    def test_true_range_uses_high_low_when_largest(self):

        service = AtrService()

        candle = {"high": 110.0, "low": 100.0, "close": 105.0}

        tr = service.calculate_true_range(
            current_candle=candle,
            previous_close=105.0
        )

        assert tr == 10.0

    def test_true_range_uses_high_close_gap_when_largest(self):

        service = AtrService()

        candle = {"high": 110.0, "low": 105.0, "close": 108.0}

        # gap up: previous close far below current low
        tr = service.calculate_true_range(
            current_candle=candle,
            previous_close=90.0
        )

        assert tr == 20.0

    def test_true_range_zero_with_invalid_previous_close(self):

        service = AtrService()

        candle = {"high": 110.0, "low": 100.0, "close": 105.0}

        tr = service.calculate_true_range(
            current_candle=candle,
            previous_close=0.0
        )

        assert tr == 0.0


class TestCalculateAtr:

    def test_returns_none_during_warmup(self):

        service = AtrService()

        service.update_candle(1, "BTCUSDT", 105, 95, 100)

        atr = service.calculate_atr(
            user_id=1,
            symbol="BTCUSDT",
            period=14
        )

        assert atr is None

    def test_returns_value_once_enough_candles(self):

        service = AtrService()

        price = 100.0

        for _ in range(20):

            service.update_candle(
                user_id=1,
                symbol="BTCUSDT",
                high=price + 2,
                low=price - 2,
                close=price
            )

            price += 0.5

        atr = service.calculate_atr(
            user_id=1,
            symbol="BTCUSDT",
            period=14
        )

        assert atr is not None

        assert atr > 0

    def test_unknown_symbol_returns_none(self):

        service = AtrService()

        atr = service.calculate_atr(
            user_id=999,
            symbol="DOESNOTEXIST",
            period=14
        )

        assert atr is None


class TestCalculateAtrPercent:

    def test_returns_none_during_warmup(self):

        service = AtrService()

        atr_percent = service.calculate_atr_percent(
            user_id=1,
            symbol="BTCUSDT",
            period=14
        )

        assert atr_percent is None

    def test_returns_positive_percent_with_enough_data(self):

        service = AtrService()

        price = 100.0

        for _ in range(20):

            service.update_candle(
                user_id=1,
                symbol="BTCUSDT",
                high=price + 2,
                low=price - 2,
                close=price
            )

            price += 0.5

        atr_percent = service.calculate_atr_percent(
            user_id=1,
            symbol="BTCUSDT",
            period=14
        )

        assert atr_percent is not None

        assert atr_percent > 0


class TestGetVolatilityRegime:

    def test_unknown_during_warmup(self):

        service = AtrService()

        regime = service.get_volatility_regime(
            user_id=1,
            symbol="BTCUSDT"
        )

        assert regime == "UNKNOWN"

    def test_returns_valid_regime_label(self):

        service = AtrService()

        price = 100.0

        for _ in range(20):

            service.update_candle(
                user_id=1,
                symbol="BTCUSDT",
                high=price + 2,
                low=price - 2,
                close=price
            )

            price += 0.5

        regime = service.get_volatility_regime(
            user_id=1,
            symbol="BTCUSDT"
        )

        assert regime in ("LOW", "NORMAL", "HIGH")


class TestReset:

    def test_reset_clears_market_data(self):

        service = AtrService()

        service.update_candle(1, "BTCUSDT", 105, 95, 100)

        service.reset()

        assert service.get_candles(1, "BTCUSDT") == []
