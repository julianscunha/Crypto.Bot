# -*- coding: utf-8 -*-

from collections import (
    defaultdict
)


class MarketRegimeService:

    def __init__(self):

        self.market_prices = (
            defaultdict(list)
        )

        self.last_regime = {}

        self.max_history = 200

        self.minimum_warmup = 20

        self.lookback_window = 50

    # =====================================================
    # UPDATE PRICE
    # =====================================================

    def update_price(
        self,
        symbol: str,
        close: float
    ):

        # =================================================
        # SAFETY
        # =================================================

        if close <= 0:

            return

        prices = (
            self.market_prices[symbol]
        )

        prices.append(
            close
        )

        # =================================================
        # MEMORY LIMIT
        # =================================================

        if len(prices) > self.max_history:

            prices.pop(0)

    # =====================================================
    # GET PRICES
    # =====================================================

    def get_prices(
        self,
        symbol: str
    ):

        return self.market_prices[
            symbol
        ]

    # =====================================================
    # DETECT REGIME
    # =====================================================

    def detect_regime(
        self,
        symbol: str
    ):

        prices = self.get_prices(
            symbol
        )

        # =================================================
        # WARMUP
        # =================================================

        if len(prices) < self.minimum_warmup:

            return "UNKNOWN"

        recent = prices[
            -self.lookback_window:
        ]

        if len(recent) < 2:

            return "UNKNOWN"

        first_price = recent[0]

        last_price = recent[-1]

        # =================================================
        # SAFETY
        # =================================================

        if first_price <= 0:

            return "UNKNOWN"

        variation_percent = round(

            (
                (
                    last_price
                    -
                    first_price
                )

                / first_price
            ) * 100,

            4
        )

        # =================================================
        # STRONG BULLISH
        # =================================================

        if variation_percent >= 3.0:

            return "BULLISH"

        # =================================================
        # STRONG BEARISH
        # =================================================

        if variation_percent <= -3.0:

            return "BEARISH"

        # =================================================
        # TRENDING
        # =================================================

        if abs(variation_percent) >= 1.0:

            return "TRENDING"

        # =================================================
        # SIDEWAYS
        # =================================================

        return "SIDEWAYS"

    # =====================================================
    # HAS CHANGED
    # =====================================================

    def has_changed(
        self,
        symbol: str,
        regime: str
    ) -> bool:

        previous = (
            self.last_regime.get(symbol)
        )

        if previous == regime:

            return False

        self.last_regime[symbol] = (
            regime
        )

        return True


market_regime_service = (
    MarketRegimeService()
)