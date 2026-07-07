# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

from core.config.trading_config import (
    positive_float
)

STRATEGY_CONFIG = {

    "minimum_signal_strength":

        positive_float(

            getattr(
                settings,
                "MINIMUM_SIGNAL_STRENGTH",
                0.50
            ),

            0.50
        )
}
