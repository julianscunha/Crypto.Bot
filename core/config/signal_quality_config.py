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
# SIGNAL QUALITY CONFIG
# =====================================================

SIGNAL_QUALITY_CONFIG = {

    # =================================================
    # SIGNAL CONFIDENCE
    # =================================================

    "minimum_signal_confidence":

        percentage(

            getattr(
                settings,
                "MIN_SIGNAL_CONFIDENCE",
                0.45
            ),

            0.45,

            minimum=0.10,

            maximum=1.00
        ),

    # =================================================
    # SIGNAL COOLDOWN
    # =================================================

    "enable_signal_cooldown":

        boolean(

            getattr(
                settings,
                "ENABLE_SIGNAL_COOLDOWN",
                True
            ),

            True
        ),

    "signal_cooldown_seconds":

        positive_int(

            getattr(
                settings,
                "SIGNAL_COOLDOWN_SECONDS",
                5
            ),

            5
        ),

    # =================================================
    # TREND FILTER
    # =================================================

    "enable_ema_trend_filter":

        boolean(

            getattr(
                settings,
                "ENABLE_EMA_TREND_FILTER",
                True
            ),

            True
        ),

    "ema_fast_period":

        positive_int(

            getattr(
                settings,
                "EMA_FAST_PERIOD",
                9
            ),

            9
        ),

    "ema_slow_period":

        positive_int(

            getattr(
                settings,
                "EMA_SLOW_PERIOD",
                21
            ),

            21
        ),

    "minimum_trend_strength_percent":

        positive_float(

            getattr(
                settings,
                "MIN_TREND_STRENGTH_PERCENT",
                0.15
            ),

            0.15
        ),

    # =================================================
    # VOLATILITY FILTER
    # =================================================

    "enable_volatility_filter":

        boolean(

            getattr(
                settings,
                "ENABLE_VOLATILITY_FILTER",
                True
            ),

            True
        ),

    "atr_validation_period":

        positive_int(

            getattr(
                settings,
                "ATR_VALIDATION_PERIOD",
                14
            ),

            14
        ),

    "minimum_atr_percent":

        positive_float(

            getattr(
                settings,
                "MINIMUM_ATR_PERCENT",
                0.01
            ),

            0.01
        ),

    # =================================================
    # POSITION CONTROL
    # =================================================

    "maximum_open_positions":

        positive_int(

            getattr(
                settings,
                "MAXIMUM_OPEN_POSITIONS",
                3
            ),

            3
        ),

    # =================================================
    # DRAWDOWN PROTECTION
    # =================================================

    "enable_drawdown_protection":

        boolean(

            getattr(
                settings,
                "ENABLE_DRAWDOWN_PROTECTION",
                True
            ),

            True
        ),

    "maximum_daily_drawdown_percent":

        percentage(

            getattr(
                settings,
                "MAXIMUM_DAILY_DRAWDOWN_PERCENT",
                5.0
            ),

            5.0,

            minimum=0.5,

            maximum=100.0
        ),

    # =================================================
    # MARKET REGIME
    # =================================================

    "enable_market_regime_alignment":

        boolean(

            getattr(
                settings,
                "ENABLE_MARKET_REGIME_ALIGNMENT",
                False
            ),

            False
        ),

    # =================================================
    # SIGNAL SPACING
    # =================================================

    "minimum_signal_spacing_candles":

        positive_int(

            getattr(
                settings,
                "MINIMUM_SIGNAL_SPACING_CANDLES",
                1
            ),

            1
        ),

    # =================================================
    # ADVANCED FILTERING
    # =================================================

    "enable_adaptive_signal_filters":

        boolean(

            getattr(
                settings,
                "ENABLE_ADAPTIVE_SIGNAL_FILTERS",
                False
            ),

            False
        ),

    "enable_dynamic_cooldown":

        boolean(

            getattr(
                settings,
                "ENABLE_DYNAMIC_COOLDOWN",
                False
            ),

            False
        ),

    "enable_weighted_signal_validation":

        boolean(

            getattr(
                settings,
                "ENABLE_WEIGHTED_SIGNAL_VALIDATION",
                False
            ),

            False
        )
}