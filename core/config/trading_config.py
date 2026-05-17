# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

# =====================================================
# SAFETY HELPERS
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

# =====================================================
# TRADING CONFIG
# =====================================================

TRADING_CONFIG = {

    # =================================================
    # POSITION
    # =================================================

    "risk_per_trade_percent":

        percentage(
            settings.RISK_PER_TRADE_PERCENT,
            1.0
        ),

    "account_balance":

        positive_float(
            settings.ACCOUNT_BALANCE,
            1000.0
        ),

    "max_open_positions":

        positive_int(
            settings.MAX_OPEN_POSITIONS,
            3
        ),

    "max_position_exposure_percent":

        percentage(
            settings.MAX_POSITION_EXPOSURE_PERCENT,
            25.0
        ),

    "max_daily_loss_percent":

        percentage(
            settings.MAX_DAILY_LOSS_PERCENT,
            5.0
        ),

    "max_daily_trades":

        positive_int(
            settings.MAX_DAILY_TRADES,
            20
        ),

    # =================================================
    # ATR RISK
    # =================================================

    "atr_period":

        positive_int(
            getattr(
                settings,
                "ATR_PERIOD",
                14
            ),
            14
        ),

    "atr_stop_multiplier":

        positive_float(
            settings.ATR_STOP_MULTIPLIER,
            1.0
        ),

    "atr_take_profit_multiplier":

        positive_float(
            settings.ATR_TAKE_PROFIT_MULTIPLIER,
            2.0
        ),

    "atr_trailing_multiplier":

        positive_float(
            settings.ATR_TRAILING_MULTIPLIER,
            1.0
        ),

    # =================================================
    # STRUCTURE
    # =================================================

    "min_structure_candles":

        positive_int(
            settings.MIN_STRUCTURE_CANDLES,
            20
        ),

    # =================================================
    # MARKET
    # =================================================

    "symbols":

        settings.SYMBOLS,

    "kline_interval":

        settings.KLINE_INTERVAL,

    # =================================================
    # EXECUTION
    # =================================================

    "mode":

        settings.MODE,

    "paper_execution":

        bool(
            settings.ENABLE_PAPER_EXECUTION
        ),

    "enable_optimizer":

        bool(
            settings.ENABLE_OPTIMIZER
        ),

    "enable_market_regime":

        bool(
            settings.ENABLE_MARKET_REGIME
        ),

    "enable_replay":

        bool(
            settings.ENABLE_REPLAY
        ),

    # =================================================
    # BINANCE
    # =================================================

    "binance_testnet":

        bool(
            settings.BINANCE_TESTNET
        )
}