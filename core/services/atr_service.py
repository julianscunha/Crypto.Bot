# -*- coding: utf-8 -*-

from collections import defaultdict

from core.config.trading_config import (
    TRADING_CONFIG
)


class AtrService:

    def __init__(self):

        self.market_data = (
            defaultdict(list)
        )

        self.max_candles = 500

    # =====================================================
    # UPDATE CANDLE
    # =====================================================

    def update_candle(
        self,
        user_id: int,
        symbol: str,
        high: float,
        low: float,
        close: float
    ):

        key = (
            user_id,
            symbol
        )

        candles = (
            self.market_data[key]
        )

        candles.append(

            {
                "high": high,
                "low": low,
                "close": close
            }
        )

        # =================================================
        # MEMORY LIMIT
        # =================================================

        if len(candles) > self.max_candles:

            candles.pop(0)

    # =====================================================
    # GET CANDLES
    # =====================================================

    def get_candles(
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
    # TRUE RANGE
    # =====================================================

    def calculate_true_range(
        self,
        current_candle,
        previous_close
    ):

        high_low = (
            current_candle["high"]
            - current_candle["low"]
        )

        high_close = abs(
            current_candle["high"]
            - previous_close
        )

        low_close = abs(
            current_candle["low"]
            - previous_close
        )

        return max(
            high_low,
            high_close,
            low_close
        )

    # =====================================================
    # ATR
    # =====================================================

    def calculate_atr(
        self,
        user_id: int,
        symbol: str,
        period: int = None
    ):

        if period is None:

            period = (
                TRADING_CONFIG[
                    "atr_period"
                ]
            )

        candles = self.get_candles(
            user_id,
            symbol
        )

        # =================================================
        # WARMUP
        # =================================================

        if len(candles) < period + 1:

            return None

        true_ranges = []

        for index in range(
            1,
            len(candles)
        ):

            current = (
                candles[index]
            )

            previous = (
                candles[index - 1]
            )

            tr = (
                self.calculate_true_range(
                    current,
                    previous["close"]
                )
            )

            true_ranges.append(
                tr
            )

        recent_true_ranges = (
            true_ranges[-period:]
        )

        if not recent_true_ranges:

            return None

        atr = (
            sum(recent_true_ranges)
            / period
        )

        return round(
            atr,
            8
        )

    # =====================================================
    # ATR PERCENT
    # =====================================================

    def calculate_atr_percent(
        self,
        user_id: int,
        symbol: str,
        period: int = None
    ):

        if period is None:

            period = (
                TRADING_CONFIG[
                    "atr_period"
                ]
            )

        candles = self.get_candles(
            user_id,
            symbol
        )

        if len(candles) < period + 1:

            return None

        atr = self.calculate_atr(
            user_id,
            symbol,
            period
        )

        if atr is None:

            return None

        current_close = (
            candles[-1]["close"]
        )

        # =================================================
        # SAFETY
        # =================================================

        if current_close <= 0:

            return None

        atr_percent = (
            atr / current_close
        ) * 100

        return round(
            atr_percent,
            4
        )


atr_service = (
    AtrService()
)