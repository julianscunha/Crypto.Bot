# -*- coding: utf-8 -*-

from collections import (
    defaultdict
)

from core.config.atr_config import (
    ATR_CONFIG
)


class AtrService:

    def __init__(self):

        self.config = (
            ATR_CONFIG
        )

        # =================================================
        # MARKET MEMORY
        # =================================================

        self.market_data = (
            defaultdict(list)
        )

        self.max_candles = (
            self.config[
                "maximum_candle_history"
            ]
        )

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        self.market_data.clear()

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

        high = self._safe_float(
            high
        )

        low = self._safe_float(
            low
        )

        close = self._safe_float(
            close
        )

        # =================================================
        # VALIDATION
        # =================================================

        if high <= 0:

            return

        if low <= 0:

            return

        if close <= 0:

            return

        if low > high:

            return

        key = self._build_key(
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
        # MEMORY CONTROL
        # =================================================

        if len(candles) > self.max_candles:

            del candles[0]

    # =====================================================
    # GET CANDLES
    # =====================================================

    def get_candles(
        self,
        user_id: int,
        symbol: str
    ):

        key = self._build_key(
            user_id,
            symbol
        )

        return self.market_data.get(
            key,
            []
        )

    # =====================================================
    # TRUE RANGE
    # =====================================================

    def calculate_true_range(
        self,
        current_candle,
        previous_close
    ):

        previous_close = (
            self._safe_float(
                previous_close
            )
        )

        if previous_close <= 0:

            return 0.0

        high_low = (

            current_candle["high"]
            -
            current_candle["low"]
        )

        high_close = abs(

            current_candle["high"]
            -
            previous_close
        )

        low_close = abs(

            current_candle["low"]
            -
            previous_close
        )

        return round(

            max(

                high_low,

                high_close,

                low_close
            ),

            8
        )

    # =====================================================
    # TRUE RANGES
    # =====================================================

    def calculate_true_ranges(
        self,
        candles
    ):

        if len(candles) < 2:

            return []

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

        return true_ranges

    # =====================================================
    # ATR
    # =====================================================

    def calculate_atr(
        self,
        user_id: int,
        symbol: str,
        period: int | None = None
    ):

        if period is None:

            period = (
                self.config[
                    "default_atr_period"
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

        true_ranges = (
            self.calculate_true_ranges(
                candles
            )
        )

        if not true_ranges:

            return None

        recent_true_ranges = (
            true_ranges[-period:]
        )

        if len(recent_true_ranges) < period:

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
        period: int | None = None
    ):

        if period is None:

            period = (
                self.config[
                    "default_atr_period"
                ]
            )

        candles = self.get_candles(

            user_id,

            symbol
        )

        if len(candles) < period + 1:

            return None

        atr = (
            self.calculate_atr(

                user_id=user_id,

                symbol=symbol,

                period=period
            )
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
            atr
            /
            current_close
        ) * 100

        return round(
            atr_percent,
            4
        )

    # =====================================================
    # VOLATILITY REGIME
    # =====================================================

    def get_volatility_regime(
        self,
        user_id: int,
        symbol: str,
        period: int | None = None
    ):

        atr_percent = (
            self.calculate_atr_percent(

                user_id=user_id,

                symbol=symbol,

                period=period
            )
        )

        if atr_percent is None:

            return "UNKNOWN"

        low_threshold = (
            self.config[
                "low_volatility_threshold"
            ]
        )

        high_threshold = (
            self.config[
                "high_volatility_threshold"
            ]
        )

        if atr_percent < low_threshold:

            return "LOW"

        if atr_percent > high_threshold:

            return "HIGH"

        return "NORMAL"


atr_service = (
    AtrService()
)