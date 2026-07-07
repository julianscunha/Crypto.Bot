# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

from core.config.signal_quality_config import (
    positive_float,
    positive_int
)

INDICATORS_CONFIG = {

    "default_ema_period":

        positive_int(

            getattr(
                settings,
                "DEFAULT_EMA_PERIOD",
                14
            ),

            14
        ),

    "default_rsi_period":

        positive_int(

            getattr(
                settings,
                "DEFAULT_RSI_PERIOD",
                14
            ),

            14
        ),

    "default_atr_period":

        positive_int(

            getattr(
                settings,
                "DEFAULT_ATR_PERIOD",
                14
            ),

            14
        ),

    "division_safety_epsilon":

        positive_float(

            getattr(
                settings,
                "INDICATOR_DIVISION_EPSILON",
                0.0001
            ),

            0.0001
        )
}
