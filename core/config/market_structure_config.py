# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

# =====================================================
# HELPERS
# =====================================================

def positive_int(
    value,
    fallback
):

    try:

        value = int(value)

        if value <= 0:

            return fallback

        return value

    except Exception:

        return fallback


def positive_float(
    value,
    fallback
):

    try:

        value = float(value)

        if value <= 0:

            return fallback

        return value

    except Exception:

        return fallback


def percentage(
    value,
    fallback,
    minimum=0.0,
    maximum=100.0
):

    try:

        value = float(value)

        if value < minimum:

            return fallback

        if value > maximum:

            return fallback

        return value

    except Exception:

        return fallback


def boolean(
    value,
    fallback
):

    if isinstance(
        value,
        bool
    ):

        return value

    if value is None:

        return fallback

    return str(value).strip().lower() in [

        "1",

        "true",

        "yes",

        "on"
    ]

# =====================================================
# MARKET STRUCTURE CONFIG
# =====================================================

MARKET_STRUCTURE_CONFIG = {

    # =================================================
    # MEMORY
    # =================================================

    "maximum_price_history":

        positive_int(

            getattr(
                settings,
                "STRUCTURE_MAX_PRICE_HISTORY",
                300
            ),

            300
        ),

    # =================================================
    # SWING DETECTION
    # =================================================

    "swing_detection_window":

        positive_int(

            getattr(
                settings,
                "STRUCTURE_SWING_WINDOW",
                2
            ),

            2
        ),

    "minimum_required_swings":

        positive_int(

            getattr(
                settings,
                "STRUCTURE_MIN_REQUIRED_SWINGS",
                2
            ),

            2
        ),

    # =================================================
    # STRUCTURE VALIDATION
    # =================================================

    "minimum_structure_candles":

        positive_int(

            getattr(
                settings,
                "STRUCTURE_MIN_CANDLES",
                20
            ),

            20
        ),

    "minimum_structure_score":

        positive_float(

            getattr(
                settings,
                "STRUCTURE_MIN_SCORE",
                2.0
            ),

            2.0
        ),

    # =================================================
    # IMPULSE
    # =================================================

    "minimum_impulse_window":

        positive_int(

            getattr(
                settings,
                "STRUCTURE_MIN_IMPULSE_WINDOW",
                5
            ),

            5
        ),

    "minimum_impulse_percent":

        positive_float(

            getattr(
                settings,
                "STRUCTURE_MIN_IMPULSE_PERCENT",
                0.10
            ),

            0.10
        ),

    "impulse_score":

        positive_float(

            getattr(
                settings,
                "STRUCTURE_IMPULSE_SCORE",
                1.0
            ),

            1.0
        ),

    # =================================================
    # STRUCTURE SCORING
    # =================================================

    "bullish_high_score":

        positive_float(

            getattr(
                settings,
                "STRUCTURE_BULLISH_HIGH_SCORE",
                1.0
            ),

            1.0
        ),

    "bullish_low_score":

        positive_float(

            getattr(
                settings,
                "STRUCTURE_BULLISH_LOW_SCORE",
                1.0
            ),

            1.0
        ),

    # =================================================
    # CONSOLIDATION FILTER
    # =================================================

    "enable_consolidation_filter":

        boolean(

            getattr(
                settings,
                "STRUCTURE_ENABLE_CONSOLIDATION_FILTER",
                True
            ),

            True
        ),

    "minimum_consolidation_window":

        positive_int(

            getattr(
                settings,
                "STRUCTURE_MIN_CONSOLIDATION_WINDOW",
                10
            ),

            10
        ),

    "maximum_consolidation_range_percent":

        positive_float(

            getattr(
                settings,
                "STRUCTURE_MAX_CONSOLIDATION_RANGE",
                0.30
            ),

            0.30
        )
}