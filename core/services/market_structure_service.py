# -*- coding: utf-8 -*-

from collections import (
    defaultdict
)

from core.config.market_structure_config import (
    MARKET_STRUCTURE_CONFIG
)


class MarketStructureService:

    def __init__(self):

        self.config = (
            MARKET_STRUCTURE_CONFIG
        )

        self.market_data = (
            defaultdict(list)
        )

        self.max_history = 300

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        self.market_data.clear()

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

        history = (
            self.market_data[key]
        )

        history.append(
            price
        )

        # =================================================
        # MEMORY LIMIT
        # =================================================

        if len(history) > self.max_history:

            history.pop(0)

    # =====================================================
    # GET PRICES
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

        # =================================================
        # SAFETY
        # =================================================

        if (
            index - window < 0
            or
            index + window >= len(prices)
        ):

            return False

        current = (
            prices[index]
        )

        left = (
            prices[
                index - window:index
            ]
        )

        right = (
            prices[
                index + 1:index + window + 1
            ]
        )

        return (

            all(
                current > value
                for value in left
            )

            and

            all(
                current > value
                for value in right
            )
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

        # =================================================
        # SAFETY
        # =================================================

        if (
            index - window < 0
            or
            index + window >= len(prices)
        ):

            return False

        current = (
            prices[index]
        )

        left = (
            prices[
                index - window:index
            ]
        )

        right = (
            prices[
                index + 1:index + window + 1
            ]
        )

        return (

            all(
                current < value
                for value in left
            )

            and

            all(
                current < value
                for value in right
            )
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

        minimum_required = max(
            10,
            window * 2 + 1
        )

        # =================================================
        # WARMUP
        # =================================================

        if len(prices) < minimum_required:

            return {

                "valid": False,

                "reason": "INSUFFICIENT_DATA"
            }

        swing_highs = []

        swing_lows = []

        for index in range(
            window,
            len(prices) - window
        ):

            if self.is_swing_high(
                prices,
                index,
                window
            ):

                swing_highs.append(
                    prices[index]
                )

            if self.is_swing_low(
                prices,
                index,
                window
            ):

                swing_lows.append(
                    prices[index]
                )

        # =================================================
        # STRUCTURE VALIDATION
        # =================================================

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

        # =================================================
        # TREND STRENGTH
        # =================================================

        if (

            trend_strength

            <

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

            max_price = max(
                recent
            )

            min_price = min(
                recent
            )

            # =============================================
            # SAFETY
            # =============================================

            if min_price <= 0:

                return {

                    "valid": False,

                    "reason": "INVALID_PRICE"
                }

            range_percent = (

                (
                    max_price - min_price
                )

                / min_price
            )

            if (

                range_percent

                <

                self.config[
                    "consolidation_threshold"
                ]
            ):

                return {

                    "valid": False,

                    "reason": "CONSOLIDATION"
                }

        # =================================================
        # VALID STRUCTURE
        # =================================================

        return {

            "valid": True,

            "reason": "BULLISH_STRUCTURE",

            "trend_strength": trend_strength
        }


market_structure_service = (
    MarketStructureService()
)