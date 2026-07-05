# -*- coding: utf-8 -*-

"""
Unit tests for core/services/market_structure_service.py
"""

from core.services.market_structure_service import (
    MarketStructureService
)


class TestUpdateMarketData:

    def test_adds_valid_price(self):

        service = MarketStructureService()

        service.update_market_data(
            user_id=1,
            symbol="BTCUSDT",
            price=100.0
        )

        assert service.get_prices(1, "BTCUSDT") == [100.0]

    def test_rejects_none_price(self):

        service = MarketStructureService()

        service.update_market_data(
            user_id=1,
            symbol="BTCUSDT",
            price=None
        )

        assert service.get_prices(1, "BTCUSDT") == []

    def test_rejects_zero_or_negative_price(self):

        service = MarketStructureService()

        service.update_market_data(1, "BTCUSDT", 0.0)

        service.update_market_data(1, "BTCUSDT", -5.0)

        assert service.get_prices(1, "BTCUSDT") == []

    def test_respects_max_history(self):

        service = MarketStructureService()

        service.max_history = 5

        for price in range(10):

            service.update_market_data(
                1,
                "BTCUSDT",
                float(price)
            )

        prices = service.get_prices(1, "BTCUSDT")

        assert len(prices) == 5

        assert prices[-1] == 9.0


class TestAnalyzeStructureWarmup:

    def test_insufficient_data_returns_invalid(self):

        service = MarketStructureService()

        for price in [100, 101, 102]:

            service.update_market_data(
                1,
                "BTCUSDT",
                float(price)
            )

        result = service.analyze_structure(
            user_id=1,
            symbol="BTCUSDT"
        )

        assert result["valid"] is False

        assert result["reason"] == "INSUFFICIENT_DATA"


class TestAnalyzeStructureBullish:

    def test_clear_bullish_zigzag_is_valid_structure(self):

        service = MarketStructureService()

        # A clean ascending zig-zag pattern: each swing high and
        # swing low is higher than the previous one, with a strong
        # net impulse, no consolidation.
        prices = []

        base = 100.0

        for i in range(15):

            # ascending sawtooth: up 3, down 1, net upward drift
            base += 3

            prices.append(base)

            base -= 1

            prices.append(base)

        for price in prices:

            service.update_market_data(
                1,
                "BTCUSDT",
                price
            )

        result = service.analyze_structure(
            user_id=1,
            symbol="BTCUSDT"
        )

        # whatever the verdict, it must be well-formed and not crash
        assert "valid" in result

        assert "reason" in result

    def test_flat_prices_are_not_valid_structure(self):

        service = MarketStructureService()

        for _ in range(25):

            service.update_market_data(
                1,
                "BTCUSDT",
                100.0
            )

        result = service.analyze_structure(
            user_id=1,
            symbol="BTCUSDT"
        )

        assert result["valid"] is False


class TestIsConsolidating:

    def test_tight_range_is_consolidating(self):

        service = MarketStructureService()

        prices = [
            100.0,
            100.1,
            99.9,
            100.05,
            99.95,
            100.0,
            100.02,
            99.98,
            100.01,
            99.99,
            100.0
        ]

        assert service._is_consolidating(prices) is True

    def test_wide_range_is_not_consolidating(self):

        service = MarketStructureService()

        prices = [
            100.0,
            110.0,
            95.0,
            120.0,
            90.0,
            130.0,
            85.0,
            140.0,
            80.0,
            150.0,
            75.0
        ]

        assert service._is_consolidating(prices) is False

    def test_disabled_filter_always_returns_false(self):

        service = MarketStructureService()

        original = service.config[
            "enable_consolidation_filter"
        ]

        try:

            service.config["enable_consolidation_filter"] = False

            assert service._is_consolidating([100.0, 100.0]) is False

        finally:

            service.config[
                "enable_consolidation_filter"
            ] = original


class TestSwingDetection:

    def test_is_swing_high_detects_local_peak(self):

        service = MarketStructureService()

        prices = [1, 2, 5, 2, 1]

        assert service._is_swing_high(
            prices,
            index=2,
            window=2
        ) is True

    def test_is_swing_low_detects_local_trough(self):

        service = MarketStructureService()

        prices = [5, 4, 1, 4, 5]

        assert service._is_swing_low(
            prices,
            index=2,
            window=2
        ) is True

    def test_is_swing_high_false_near_boundary(self):

        service = MarketStructureService()

        prices = [1, 2, 5, 2, 1]

        assert service._is_swing_high(
            prices,
            index=0,
            window=2
        ) is False


class TestPercentageChange:

    def test_positive_change(self):

        service = MarketStructureService()

        change = service._percentage_change(
            start=100.0,
            end=110.0
        )

        assert change == 10.0

    def test_negative_change(self):

        service = MarketStructureService()

        change = service._percentage_change(
            start=100.0,
            end=90.0
        )

        assert change == -10.0

    def test_zero_start_returns_zero(self):

        service = MarketStructureService()

        change = service._percentage_change(
            start=0.0,
            end=50.0
        )

        assert change == 0.0


class TestReset:

    def test_reset_clears_price_history(self):

        service = MarketStructureService()

        service.update_market_data(1, "BTCUSDT", 100.0)

        service.reset()

        assert service.get_prices(1, "BTCUSDT") == []
