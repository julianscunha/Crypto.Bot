# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

# =====================================================
# HELPERS
# =====================================================

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
# TRADE MANAGEMENT CONFIG
# =====================================================

TRADE_MANAGEMENT_CONFIG = {

    # =================================================
    # TRAILING STOP
    # =================================================

    "enable_trailing_stop":

        boolean(

            getattr(
                settings,
                "ENABLE_TRAILING_STOP",
                True
            ),

            True
        ),

    "enable_atr_trailing":

        boolean(

            getattr(
                settings,
                "ENABLE_ATR_TRAILING",
                False
            ),

            False
        ),

    "atr_trailing_multiplier":

        positive_float(

            getattr(
                settings,
                "ATR_TRAILING_MULTIPLIER",
                1.0
            ),

            1.0
        ),

    # =================================================
    # BREAKEVEN
    # =================================================

    "enable_breakeven":

        boolean(

            getattr(
                settings,
                "ENABLE_BREAKEVEN",
                True
            ),

            True
        ),

    "breakeven_trigger_percent":

        percentage(

            getattr(
                settings,
                "BREAKEVEN_TRIGGER_PERCENT",
                0.50
            ),

            0.50,

            minimum=0.05,

            maximum=100.0
        ),

    # =================================================
    # PARTIAL EXIT
    # =================================================

    "enable_partial_take_profit":

        boolean(

            getattr(
                settings,
                "ENABLE_PARTIAL_TAKE_PROFIT",
                False
            ),

            False
        ),

    "partial_take_profit_percent":

        percentage(

            getattr(
                settings,
                "PARTIAL_TAKE_PROFIT_PERCENT",
                50.0
            ),

            50.0,

            minimum=1.0,

            maximum=100.0
        ),

    # =================================================
    # POSITION MANAGEMENT
    # =================================================

    "enable_dynamic_take_profit":

        boolean(

            getattr(
                settings,
                "ENABLE_DYNAMIC_TAKE_PROFIT",
                False
            ),

            False
        ),

    "enable_volatility_based_management":

        boolean(

            getattr(
                settings,
                "ENABLE_VOLATILITY_BASED_MANAGEMENT",
                False
            ),

            False
        )
}