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
# TRADING CONFIG
# =====================================================

TRADING_CONFIG = {

    # =================================================
    # ACCOUNT
    # =================================================

    "account_balance":

        positive_float(

            getattr(
                settings,
                "ACCOUNT_BALANCE",
                1000.0
            ),

            1000.0
        ),

    # =================================================
    # RISK MANAGEMENT
    # =================================================

    "risk_per_trade_percent":

        percentage(

            getattr(
                settings,
                "RISK_PER_TRADE_PERCENT",
                1.0
            ),

            1.0,

            minimum=0.1,

            maximum=100.0
        ),

    "max_position_exposure_percent":

        percentage(

            getattr(
                settings,
                "MAX_POSITION_EXPOSURE_PERCENT",
                25.0
            ),

            25.0,

            minimum=1.0,

            maximum=100.0
        ),

    "max_daily_loss_percent":

        percentage(

            getattr(
                settings,
                "MAX_DAILY_LOSS_PERCENT",
                5.0
            ),

            5.0,

            minimum=0.5,

            maximum=100.0
        ),

    "max_daily_trades":

        positive_int(

            getattr(
                settings,
                "MAX_DAILY_TRADES",
                20
            ),

            20
        ),

    # =================================================
    # ATR RISK MODEL
    # =================================================

    "atr_stop_multiplier":

        positive_float(

            getattr(
                settings,
                "ATR_STOP_MULTIPLIER",
                1.0
            ),

            1.0
        ),

    "atr_take_profit_multiplier":

        positive_float(

            getattr(
                settings,
                "ATR_TAKE_PROFIT_MULTIPLIER",
                2.0
            ),

            2.0
        ),

    "minimum_risk_reward_ratio":

        positive_float(

            getattr(
                settings,
                "MINIMUM_RISK_REWARD_RATIO",
                1.2
            ),

            1.2
        ),

    # =================================================
    # MARKET STRUCTURE
    # =================================================

    "minimum_structure_candles":

        positive_int(

            getattr(
                settings,
                "MINIMUM_STRUCTURE_CANDLES",
                20
            ),

            20
        ),

    # =================================================
    # EXECUTION MODE
    # =================================================

    "runtime_mode":

        getattr(
            settings,
            "MODE",
            "PAPER"
        ),

    "paper_execution":

        boolean(

            getattr(
                settings,
                "ENABLE_PAPER_EXECUTION",
                True
            ),

            True
        )
}
