# -*- coding: utf-8 -*-

from collections import defaultdict


class MarketRegimeService:

    def __init__(self):

        self.market_prices = (
            defaultdict(list)
        )

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

        prices.append(close)
        
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

        if len(prices) < 20:

            return "UNKNOWN"

        recent = prices[-50:]

        first_price = recent[0]

        last_price = recent[-1]

        variation = (
            (last_price - first_price)
            / first_price
        )

        # =================================================
        # BULLISH
        # =================================================

        if variation > 0.02:

            return "BULLISH"

        # =================================================
        # BEARISH
        # =================================================

        if variation < -0.02:

            return "BEARISH"

        # =================================================
        # SIDEWAYS
        # =================================================

        return "SIDEWAYS"


market_regime_service = (
    MarketRegimeService()
)