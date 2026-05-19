# -*- coding: utf-8 -*-

from collections import (
    defaultdict
)

from statistics import (
    mean
)

from core.config.market_structure_config import (
    MARKET_STRUCTURE_CONFIG
)


class MarketStructureService:

    def __init__(self):

        self.config = (
            MARKET_STRUCTURE_CONFIG
        )

        # =================================================
        # MARKET CACHE
        # =================================================

        self.market_prices = (
            defaultdict(list)
        )

        # =================================================
        # MEMORY
        # =================================================

        self.max_history = (
            self.config[
                "maximum_price_history"
            ]
        )

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        self.market_prices.clear()

    # =====================================================
    # CACHE KEY
    # =====================================================

    @staticmethod
    def _build_key(
        user_id: int,
        symbol: str
    ):

        return (
            user_id,
            symbol
        )

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _safe_mean(
        values
    ):

        if not values:

            return 0.0

        return mean(values)

    @staticmethod
    def _percentage_change(
        start: float,
        end: float
    ):

        if start <= 0:

            return 0.0

        return round(

            (
                (
                    end
                    -
                    start
                )

                / start
            ) * 100,

            4
        )

    # =====================================================
    # UPDATE MARKET DATA
    # =====================================================

    def update_market_data(
        self,
        user_id: int,
        symbol: str,
        price: float
    ):

        if price is None:

            return

        if price <= 0:

            return

        key = self._build_key(
            user_id,
            symbol
        )

        history = (
            self.market_prices[key]
        )

        history.append(
            float(price)
        )

        # =================================================
        # MEMORY CONTROL
        # =================================================

        if len(history) > self.max_history:

            del history[0]

    # =====================================================
    # GET PRICES
    # =====================================================

    def get_prices(
        self,
        user_id: int,
        symbol: str
    ):

        key = self._build_key(
            user_id,
            symbol
        )

        return self.market_prices[key]

    # =====================================================
    # SWING HIGH
    # =====================================================

    @staticmethod
    def _is_swing_high(
        prices,
        index,
        window
    ):

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

    @staticmethod
    def _is_swing_low(
        prices,
        index,
        window
    ):

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
    # SWING EXTRACTION
    # =====================================================

    def _extract_swings(
        self,
        prices,
        window
    ):

        swing_highs = []

        swing_lows = []

        for index in range(
            window,
            len(prices) - window
        ):

            if self._is_swing_high(
                prices,
                index,
                window
            ):

                swing_highs.append(
                    prices[index]
                )

            if self._is_swing_low(
                prices,
                index,
                window
            ):

                swing_lows.append(
                    prices[index]
                )

        return (
            swing_highs,
            swing_lows
        )

    # =====================================================
    # CONSOLIDATION
    # =====================================================

    def _is_consolidating(
        self,
        prices
    ):

        if not self.config[
            "enable_consolidation_filter"
        ]:

            return False

        recent_window = max(

            self.config[
                "minimum_structure_candles"
            ],

            self.config[
                "minimum_consolidation_window"
            ]
        )

        recent = prices[
            -recent_window:
        ]

        if len(recent) < 2:

            return False

        highest = max(
            recent
        )

        lowest = min(
            recent
        )

        if lowest <= 0:

            return True

        range_percent = round(

            (
                (
                    highest
                    -
                    lowest
                )

                / lowest
            ) * 100,

            4
        )

        threshold = (
            self.config[
                "maximum_consolidation_range_percent"
            ]
        )

        return (
            range_percent < threshold
        )

    # =====================================================
    # IMPULSE
    # =====================================================

    def _calculate_impulse_strength(
        self,
        prices
    ):

        recent_window = max(

            self.config[
                "minimum_structure_candles"
            ],

            self.config[
                "minimum_impulse_window"
            ]
        )

        recent = prices[
            -recent_window:
        ]

        if len(recent) < 2:

            return 0.0

        return self._percentage_change(

            recent[0],

            recent[-1]
        )

    # =====================================================
    # STRUCTURE SCORE
    # =====================================================

    def _calculate_structure_score(
        self,
        bullish_highs: bool,
        bullish_lows: bool,
        impulse_strength: float
    ):

        score = 0.0

        # =================================================
        # HIGHER HIGHS
        # =================================================

        if bullish_highs:

            score += self.config[
                "bullish_high_score"
            ]

        # =================================================
        # HIGHER LOWS
        # =================================================

        if bullish_lows:

            score += self.config[
                "bullish_low_score"
            ]

        # =================================================
        # IMPULSE
        # =================================================

        minimum_impulse = (
            self.config[
                "minimum_impulse_percent"
            ]
        )

        if impulse_strength >= minimum_impulse:

            score += self.config[
                "impulse_score"
            ]

        return round(
            score,
            2
        )

    # =====================================================
    # ANALYZE STRUCTURE
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

        swing_window = (
            self.config[
                "swing_detection_window"
            ]
        )

        minimum_required = max(

            self.config[
                "minimum_structure_candles"
            ],

            swing_window * 2 + 1
        )

        # =================================================
        # WARMUP
        # =================================================

        if len(prices) < minimum_required:

            return {

                "valid": False,

                "reason": "INSUFFICIENT_DATA"
            }

        # =================================================
        # SWINGS
        # =================================================

        swing_highs, swing_lows = (

            self._extract_swings(
                prices,
                swing_window
            )
        )

        # =================================================
        # MINIMUM STRUCTURE
        # =================================================

        minimum_swings = (
            self.config[
                "minimum_required_swings"
            ]
        )

        if len(swing_highs) < minimum_swings:

            return {

                "valid": False,

                "reason": "NO_STRUCTURE"
            }

        if len(swing_lows) < minimum_swings:

            return {

                "valid": False,

                "reason": "NO_STRUCTURE"
            }

        # =================================================
        # DIRECTION
        # =================================================

        bullish_highs = (

            swing_highs[-1]

            >

            self._safe_mean(
                swing_highs[-2:]
            )
        )

        bullish_lows = (

            swing_lows[-1]

            >

            self._safe_mean(
                swing_lows[-2:]
            )
        )

        # =================================================
        # IMPULSE
        # =================================================

        impulse_strength = (
            self._calculate_impulse_strength(
                prices
            )
        )

        # =================================================
        # SCORE
        # =================================================

        structure_score = (

            self._calculate_structure_score(

                bullish_highs,

                bullish_lows,

                impulse_strength
            )
        )

        minimum_score = (
            self.config[
                "minimum_structure_score"
            ]
        )

        if structure_score < minimum_score:

            return {

                "valid": False,

                "reason": "WEAK_STRUCTURE",

                "score": structure_score,

                "impulse_strength":
                    impulse_strength
            }

        # =================================================
        # CONSOLIDATION
        # =================================================

        if self._is_consolidating(
            prices
        ):

            return {

                "valid": False,

                "reason": "CONSOLIDATION",

                "score": structure_score
            }

        # =================================================
        # VALID STRUCTURE
        # =================================================

        return {

            "valid": True,

            "reason": "BULLISH_STRUCTURE",

            "score": structure_score,

            "impulse_strength":
                impulse_strength,

            "bullish_highs":
                bullish_highs,

            "bullish_lows":
                bullish_lows
        }


market_structure_service = (
    MarketStructureService()
)