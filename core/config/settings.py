# -*- coding: utf-8 -*-

import os

from dotenv import (
    load_dotenv
)

# =====================================================
# LOAD ENV
# =====================================================

load_dotenv()

# =====================================================
# HELPERS
# =====================================================

def env_bool(
    key: str,
    default: bool = False
) -> bool:

    value = os.getenv(
        key,
        str(default)
    )

    return str(value).strip().lower() in [

        "1",

        "true",

        "yes",

        "on"
    ]


def env_int(
    key: str,
    default: int
) -> int:

    try:

        value = int(
            os.getenv(
                key,
                default
            )
        )

        return value

    except Exception:

        return default


def env_float(
    key: str,
    default: float
) -> float:

    try:

        value = float(
            os.getenv(
                key,
                default
            )
        )

        return value

    except Exception:

        return default


def env_str(
    key: str,
    default: str
) -> str:

    value = os.getenv(
        key,
        default
    )

    return str(value).strip()


def env_list(
    key: str,
    default: str
) -> list[str]:

    raw = os.getenv(
        key,
        default
    )

    values = [

        item.strip().upper()

        for item in raw.split(",")

        if item.strip()
    ]

    # =================================================
    # UNIQUE VALUES
    # =================================================

    return list(
        dict.fromkeys(values)
    )

# =====================================================
# SETTINGS
# =====================================================

class Settings:

    # =================================================
    # ENVIRONMENT
    # =================================================

    MODE = env_str(
        "MODE",
        "paper"
    )

    # =================================================
    # API
    # =================================================

    API_HOST = env_str(
        "API_HOST",
        "127.0.0.1"
    )

    API_PORT = env_int(
        "API_PORT",
        8000
    )

    # =================================================
    # DATABASE
    # =================================================

    DATABASE_URL = env_str(
        "DATABASE_URL",
        "sqlite:///crypto_bot.db"
    )

    # =================================================
    # BINANCE
    # =================================================

    BINANCE_TESTNET = env_bool(
        "BINANCE_TESTNET",
        True
    )

    BINANCE_API_KEY = env_str(
        "BINANCE_API_KEY",
        ""
    )

    BINANCE_SECRET_KEY = env_str(
        "BINANCE_SECRET_KEY",
        ""
    )

    # =================================================
    # RISK ENGINE
    # =================================================

    ACCOUNT_BALANCE = env_float(
        "ACCOUNT_BALANCE",
        100.0
    )

    RISK_PER_TRADE_PERCENT = env_float(
        "RISK_PER_TRADE_PERCENT",
        0.25
    )

    MAX_OPEN_POSITIONS = env_int(
        "MAX_OPEN_POSITIONS",
        3
    )

    MAX_POSITION_EXPOSURE_PERCENT = env_float(
        "MAX_POSITION_EXPOSURE_PERCENT",
        5.0
    )

    MAX_DAILY_LOSS_PERCENT = env_float(
        "MAX_DAILY_LOSS_PERCENT",
        5.0
    )

    MAX_DAILY_TRADES = env_int(
        "MAX_DAILY_TRADES",
        20
    )

    # =================================================
    # ATR
    # =================================================

    ATR_PERIOD = env_int(
        "ATR_PERIOD",
        14
    )

    ATR_STOP_MULTIPLIER = env_float(
        "ATR_STOP_MULTIPLIER",
        1.0
    )

    ATR_TAKE_PROFIT_MULTIPLIER = env_float(
        "ATR_TAKE_PROFIT_MULTIPLIER",
        3.0
    )

    ATR_TRAILING_MULTIPLIER = env_float(
        "ATR_TRAILING_MULTIPLIER",
        2.0
    )

    # =================================================
    # STRUCTURE
    # =================================================

    MIN_STRUCTURE_CANDLES = env_int(
        "MIN_STRUCTURE_CANDLES",
        6
    )

    # =================================================
    # EXECUTION
    # =================================================

    ENABLE_PAPER_EXECUTION = env_bool(
        "ENABLE_PAPER_EXECUTION",
        True
    )

    ENABLE_OPTIMIZER = env_bool(
        "ENABLE_OPTIMIZER",
        False
    )

    ENABLE_MARKET_REGIME = env_bool(
        "ENABLE_MARKET_REGIME",
        True
    )

    ENABLE_REPLAY = env_bool(
        "ENABLE_REPLAY",
        False
    )

    # =================================================
    # LOGGING
    # =================================================

    LOG_LEVEL = env_str(
        "LOG_LEVEL",
        "INFO"
    )

    # =================================================
    # MARKET
    # =================================================

    SYMBOLS = env_list(
        "SYMBOLS",
        "BTCUSDT,ETHUSDT,SOLUSDT"
    )

    KLINE_INTERVAL = env_str(
        "KLINE_INTERVAL",
        "1m"
    )


settings = (
    Settings()
)