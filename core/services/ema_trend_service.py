# -*- coding: utf-8 -*-

from collections import defaultdict


class EmaTrendService:

    def __init__(self):

        self.market_history = defaultdict(list)

    # =====================================================
    # UPDATE PRICE
    # =====================================================

    def update_price(
        self,
        user_id: int,
        symbol: str,
        price: float
    ):

        key = (
            user_id,
            symbol
        )

        history = self.market_history[key]

        history.append(price)

        if len(history) > 200:

            history.pop(0)

    # =====================================================
    # EMA
    # =====================================================

    def calculate_ema(
        self,
        prices: list,
        period: int
    ):

        if len(prices) < period:
            return None

        multiplier = (
            2 / (period + 1)
        )

        ema = (
            sum(prices[:period]) / period
        )

        for price in prices[period:]:

            ema = (
                (price - ema)
                * multiplier
            ) + ema

        return ema

    # =====================================================
    # TREND VALIDATION
    # =====================================================

    def is_bullish(
        self,
        user_id: int,
        symbol: str,
        fast_period: int,
        slow_period: int
    ):

        key = (
            user_id,
            symbol
        )

        prices = self.market_history[key]

        ema_fast = self.calculate_ema(
            prices,
            fast_period
        )

        ema_slow = self.calculate_ema(
            prices,
            slow_period
        )

        if ema_fast is None:
            return False

        if ema_slow is None:
            return False

        return ema_fast > ema_slow
