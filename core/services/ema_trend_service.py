# -*- coding: utf-8 -*-

from collections import (
    defaultdict
)


class EmaTrendService:

    def __init__(self):

        self.market_history = (
            defaultdict(list)
        )

        self.max_history = 200

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

        history = (
            self.market_history[key]
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

        return self.market_history.get(
            key,
            []
        )

    # =====================================================
    # EMA
    # =====================================================

    def calculate_ema(
        self,
        prices: list,
        period: int
    ):

        # =================================================
        # SAFETY
        # =================================================

        if not prices:

            return None

        if len(prices) < period:

            return None

        multiplier = (
            2 / (period + 1)
        )

        ema = (
            sum(prices[:period])
            / period
        )

        for price in prices[period:]:

            ema = (

                (
                    price - ema
                )

                * multiplier

            ) + ema

        return round(
            ema,
            8
        )

    # =====================================================
    # BULLISH VALIDATION
    # =====================================================

    def is_bullish(
        self,
        user_id: int,
        symbol: str,
        fast_period: int,
        slow_period: int
    ):

        prices = self.get_prices(
            user_id=user_id,
            symbol=symbol
        )

        ema_fast = self.calculate_ema(
            prices=prices,
            period=fast_period
        )

        ema_slow = self.calculate_ema(
            prices=prices,
            period=slow_period
        )

        # =================================================
        # WARMUP
        # =================================================

        if ema_fast is None:

            return False

        if ema_slow is None:

            return False

        # =================================================
        # TREND
        # =================================================

        return (
            ema_fast >= ema_slow
        )


ema_trend_service = (
    EmaTrendService()
)