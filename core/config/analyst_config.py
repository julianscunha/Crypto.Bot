# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

from core.config.signal_quality_config import (
    positive_float
)

ANALYST_CONFIG = {

    # =================================================
    # CONFIDENCE MODEL
    # =================================================

    "base_confidence":

        positive_float(

            getattr(
                settings,
                "ANALYST_BASE_CONFIDENCE",
                0.50
            ),

            0.50
        ),

    "structure_bonus":

        positive_float(

            getattr(
                settings,
                "ANALYST_STRUCTURE_BONUS",
                0.20
            ),

            0.20
        ),

    "regime_bonus":

        positive_float(

            getattr(
                settings,
                "ANALYST_REGIME_BONUS",
                0.15
            ),

            0.15
        ),

    "volatility_bonus":

        positive_float(

            getattr(
                settings,
                "ANALYST_VOLATILITY_BONUS",
                0.10
            ),

            0.10
        ),

    "minimum_volatility_percent":

        positive_float(

            getattr(
                settings,
                "ANALYST_MIN_VOLATILITY_PERCENT",
                0.30
            ),

            0.30
        ),

    "maximum_confidence":

        positive_float(

            getattr(
                settings,
                "ANALYST_MAX_CONFIDENCE",
                1.0
            ),

            1.0
        ),

    # =================================================
    # REGIMES
    # =================================================

    "bullish_regimes": [

        "TRENDING",

        "BULLISH"
    ]
}