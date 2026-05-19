# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

from core.config.signal_quality_config import (
    positive_float,
    positive_int
)

ATR_CONFIG = {

    "maximum_candle_history":

        positive_int(

            getattr(
                settings,
                "ATR_MAX_CANDLE_HISTORY",
                500
            ),

            500
        ),

    "default_atr_period":

        positive_int(

            getattr(
                settings,
                "ATR_PERIOD",
                14
            ),

            14
        ),

    "low_volatility_threshold":

        positive_float(

            getattr(
                settings,
                "ATR_LOW_VOLATILITY_THRESHOLD",
                0.20
            ),

            0.20
        ),

    "high_volatility_threshold":

        positive_float(

            getattr(
                settings,
                "ATR_HIGH_VOLATILITY_THRESHOLD",
                1.50
            ),

            1.50
        )
}