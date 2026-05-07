# -*- coding: utf-8 -*-

from collections import defaultdict

from core.config.market_structure_config import (
    MARKET_STRUCTURE_CONFIG
)


class MarketStructureService:

    def __init__(self):

        self.config = MARKET_STRUCTURE_CONFIG

        self.market_data = defaultdict(list)

    # =====================================================
    # UPDATE MARKET DATA
    # =====================================================

    def update_market_data(
        self,
        user_id: int,
        symbol: str,
        price: float
    ):

        key = (
            user_id,
            symbol
        )

        history = self.market_data[key]

        history.append(price)

        if len(history) > 300:
            history.pop(0)

    # =====================================================
    # GET HISTORY
    # =====================================================

    def get_prices(
        self,
        user_id: int,
        symbol: str
    ):

        key = (
            user_id,
            symbol
        )

        return self.market_data[key]

    # =====================================================
    # SWING HIGH
    # =====================================================

    def is_swing_high(
        self,
        prices,
        index,
        window
    ):

        current = prices[index]

        left = prices[
            index - window:index
        ]

        right = prices[
            index + 1:index + window + 1
        ]

        return (
            all(current > x for x in left)
            and
            all(current > x for x in right)
        )

    # =====================================================
    # SWING LOW
    # =====================================================

    def is_swing_low(
        self,
        prices,
        index,
        window
    ):

        current = prices[index]

        left = prices[
            index - window:index
        ]

        right = prices[
            index + 1:index + window + 1
        ]

        return (
            all(current < x for x in left)
            and
            all(current < x for x in right)
        )

    # =====================================================
    # MARKET STRUCTURE
    # =====================================================

    def analyze_structure(
        self,
        user_id: int,
        symbol: str
    ):

        prices = self.get_prices(
            user_id,
            symbol
        )

        window = self.config[
            "swing_window"
        ]

        if len(prices) < 10:

            return {
                "valid": False,
                "reason": "INSUFFICIENT_DATA"
            }

        swing_highs = []

        swing_lows = []

        for i in range(
            window,
            len(prices) - window
        ):

            if self.is_swing_high(
                prices,
                i,
                window
            ):

                swing_highs.append(
                    prices[i]
                )

            if self.is_swing_low(
                prices,
                i,
                window
            ):

                swing_lows.append(
                    prices[i]
                )

        if len(swing_highs) < 2:
            return {
                "valid": False,
                "reason": "NO_STRUCTURE"
            }

        if len(swing_lows) < 2:
            return {
                "valid": False,
                "reason": "NO_STRUCTURE"
            }

        bullish_highs = (
            swing_highs[-1]
            >
            swing_highs[-2]
        )

        bullish_lows = (
            swing_lows[-1]
            >
            swing_lows[-2]
        )

        trend_strength = 0

        if bullish_highs:
            trend_strength += 1

        if bullish_lows:
            trend_strength += 1

        if (
            trend_strength <
            self.config[
                "min_trend_strength"
            ]
        ):

            return {
                "valid": False,
                "reason": "WEAK_STRUCTURE"
            }

        # =================================================
        # CONSOLIDATION FILTER
        # =================================================

        if self.config[
            "enable_consolidation_filter"
        ]:

            recent = prices[-10:]

            max_price = max(recent)

            min_price = min(recent)

            range_percent = (
                (max_price - min_price)
                / min_price
            )

            if (
                range_percent <
                self.config[
                    "consolidation_threshold"
                ]
            ):

                return {
                    "valid": False,
                    "reason": "CONSOLIDATION"
                }

        return {
            "valid": True,
            "reason": "BULLISH_STRUCTURE",
            "trend_strength": trend_strength
        }