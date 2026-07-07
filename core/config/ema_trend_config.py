# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

from core.config.signal_quality_config import (
    positive_float,
    positive_int
)

EMA_TREND_CONFIG = {

    "maximum_price_history":

        positive_int(

            getattr(
                settings,
                "EMA_MAX_HISTORY",
                300
            ),

            300
        ),

    "minimum_bullish_spread_percent":

        positive_float(

            getattr(
                settings,
                "EMA_MIN_BULLISH_SPREAD_PERCENT",
                0.0
            ),

            0.0
        )
}
