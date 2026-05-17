# -*- coding: utf-8 -*-

from collections import defaultdict


class MarketRegimeService:

    def __init__(self):

        self.market_prices = (
            defaultdict(list)
        )

        # =====================================================
        # LAST REGIME CACHE
        # =====================================================

        self.last_regime = {}

    # =====================================================
    # UPDATE PRICE
    # =====================================================

    def update_price(
        self,
        symbol: str,
        close: float
    ):

        prices = (
            self.market_prices[symbol]
        )

        prices.append(
            close
        )

        # =====================================================
        # MEMORY LIMIT
        # =====================================================

        if len(prices) > 200:

            prices.pop(0)

    # =====================================================
    # DETECT REGIME
    # =====================================================

    def detect_regime(
        self,
        symbol: str
    ):

        prices = (
            self.market_prices[symbol]
        )

        # =====================================================
        # WARMUP
        # =====================================================

        if len(prices) < 20:

            return "UNKNOWN"

        # =====================================================
        # LOOKBACK WINDOW
        # =====================================================

        recent = (
            prices[-50:]
            if len(prices) >= 50
            else prices
        )

        if len(recent) < 2:

            return "UNKNOWN"

        first_price = recent[0]

        last_price = recent[-1]

        # =====================================================
        # SAFETY
        # =====================================================

        if first_price <= 0:

            return "UNKNOWN"

        variation = (
            (last_price - first_price)
            / first_price
        )

        # =====================================================
        # BULLISH
        # =====================================================

        if variation > 0.02:

            return "BULLISH"

        # =====================================================
        # BEARISH
        # =====================================================

        if variation < -0.02:

            return "BEARISH"

        # =====================================================
        # SIDEWAYS
        # =====================================================

        return "SIDEWAYS"

    # =====================================================
    # REGIME CHANGED
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

        self.last_regime[symbol] = regime

        return True


market_regime_service = (
    MarketRegimeService()
)