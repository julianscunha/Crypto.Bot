# -*- coding: utf-8 -*-

from collections import (
    defaultdict
)

from core.config.ema_trend_config import (
    EMA_TREND_CONFIG
)


class EmaTrendService:

    def __init__(self):

        self.config = (
            EMA_TREND_CONFIG
        )

        # =================================================
        # MARKET MEMORY
        # =================================================

        self.market_history = (
            defaultdict(list)
        )

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

        self.market_history.clear()

    # =====================================================
    # HELPERS
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

    @staticmethod
    def _safe_float(
        value,
        fallback=0.0
    ):

        try:

            return float(value)

        except Exception:

            return fallback

    # =====================================================
    # UPDATE PRICE
    # =====================================================

    def update_price(
        self,
        user_id: int,
        symbol: str,
        price: float
    ):

        price = self._safe_float(
            price
        )

        if price <= 0:

            return

        key = self._build_key(
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

        if period <= 0:

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
                    price
                    -
                    ema
                )

                * multiplier

            ) + ema

        return round(
            ema,
            8
        )

    # =====================================================
    # EMA SPREAD
    # =====================================================

    def calculate_ema_spread_percent(
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

            return None

        if ema_slow is None:

            return None

        if ema_slow <= 0:

            return None

        return round(

            (
                (
                    ema_fast
                    -
                    ema_slow
                )

                / ema_slow
            ) * 100,

            4
        )

    # =====================================================
    # TREND DIRECTION
    # =====================================================

    def is_bullish(
        self,
        user_id: int,
        symbol: str,
        fast_period: int,
        slow_period: int
    ):

        spread = (
            self.calculate_ema_spread_percent(

                user_id=user_id,

                symbol=symbol,

                fast_period=fast_period,

                slow_period=slow_period
            )
        )

        if spread is None:

            return False

        minimum_spread = (
            self.config[
                "minimum_bullish_spread_percent"
            ]
        )

        return (
            spread >= minimum_spread
        )

    # =====================================================
    # TREND STRENGTH
    # =====================================================

    def get_trend_strength(
        self,
        user_id: int,
        symbol: str,
        fast_period: int,
        slow_period: int
    ):

        spread = (
            self.calculate_ema_spread_percent(

                user_id=user_id,

                symbol=symbol,

                fast_period=fast_period,

                slow_period=slow_period
            )
        )

        if spread is None:

            return 0.0

        return round(
            abs(spread),
            4
        )


ema_trend_service = (
    EmaTrendService()
)
