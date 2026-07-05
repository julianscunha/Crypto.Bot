# -*- coding: utf-8 -*-

"""
Unit tests for core/services/market_regime_service.py
"""

from core.services.market_regime_service import (
    MarketRegimeService
)


class TestUpdatePrice:

    def test_adds_valid_price(self):

        service = MarketRegimeService()

        service.update_price("BTCUSDT", 100.0)

        assert service.get_prices("BTCUSDT") == [100.0]

    def test_rejects_zero_or_negative_price(self):

        service = MarketRegimeService()

        service.update_price("BTCUSDT", 0.0)

        service.update_price("BTCUSDT", -1.0)

        assert service.get_prices("BTCUSDT") == []

    def test_respects_max_history(self):

        service = MarketRegimeService()

        service.max_history = 5

        for price in range(10):

            service.update_price("BTCUSDT", float(price + 1))

        assert len(service.get_prices("BTCUSDT")) == 5


class TestDetectRegime:

    def test_unknown_during_warmup(self):

        service = MarketRegimeService()

        for price in range(5):

            service.update_price("BTCUSDT", float(price + 100))

        assert service.detect_regime("BTCUSDT") == "UNKNOWN"

    def test_bullish_on_strong_upward_move(self):

        service = MarketRegimeService()

        for _ in range(20):

            service.update_price("BTCUSDT", 100.0)

        service.update_price("BTCUSDT", 110.0)

        assert service.detect_regime("BTCUSDT") == "BULLISH"

    def test_bearish_on_strong_downward_move(self):

        service = MarketRegimeService()

        for _ in range(20):

            service.update_price("BTCUSDT", 100.0)

        service.update_price("BTCUSDT", 90.0)

        assert service.detect_regime("BTCUSDT") == "BEARISH"

    def test_sideways_on_flat_prices(self):

        service = MarketRegimeService()

        for _ in range(25):

            service.update_price("BTCUSDT", 100.0)

        assert service.detect_regime("BTCUSDT") == "SIDEWAYS"

    def test_trending_on_moderate_move(self):

        service = MarketRegimeService()

        for _ in range(20):

            service.update_price("BTCUSDT", 100.0)

        service.update_price("BTCUSDT", 101.5)

        assert service.detect_regime("BTCUSDT") == "TRENDING"


class TestHasChanged:

    def test_true_on_first_observation(self):

        service = MarketRegimeService()

        assert service.has_changed(
            "BTCUSDT",
            "BULLISH"
        ) is True

    def test_false_when_regime_unchanged(self):

        service = MarketRegimeService()

        service.has_changed("BTCUSDT", "BULLISH")

        assert service.has_changed(
            "BTCUSDT",
            "BULLISH"
        ) is False

    def test_true_when_regime_changes(self):

        service = MarketRegimeService()

        service.has_changed("BTCUSDT", "BULLISH")

        assert service.has_changed(
            "BTCUSDT",
            "BEARISH"
        ) is True
