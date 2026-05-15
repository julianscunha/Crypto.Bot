# -*- coding: utf-8 -*-

import os

from dotenv import load_dotenv


# =====================================================
# LOAD ENV
# =====================================================

load_dotenv()


class Settings:

    # =====================================================
    # ENVIRONMENT
    # =====================================================

    MODE = os.getenv(
        "MODE",
        "paper"
    )

    # =====================================================
    # API
    # =====================================================

    API_HOST = os.getenv(
        "API_HOST",
        "127.0.0.1"
    )

    API_PORT = int(
        os.getenv(
            "API_PORT",
            8000
        )
    )

    # =====================================================
    # DATABASE
    # =====================================================

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///crypto_bot.db"
    )

    # =====================================================
    # BINANCE
    # =====================================================

    BINANCE_TESTNET = (
        os.getenv(
            "BINANCE_TESTNET",
            "true"
        ).lower() == "true"
    )

    BINANCE_API_KEY = os.getenv(
        "BINANCE_API_KEY",
        ""
    )

    BINANCE_SECRET_KEY = os.getenv(
        "BINANCE_SECRET_KEY",
        ""
    )

    # =====================================================
    # RISK ENGINE
    # =====================================================

    ACCOUNT_BALANCE = float(
        os.getenv(
            "ACCOUNT_BALANCE",
            100.0
        )
    )

    RISK_PER_TRADE_PERCENT = float(
        os.getenv(
            "RISK_PER_TRADE_PERCENT",
            0.25
        )
    )

    MAX_OPEN_POSITIONS = int(
        os.getenv(
            "MAX_OPEN_POSITIONS",
            3
        )
    )

    MAX_POSITION_EXPOSURE_PERCENT = float(
        os.getenv(
            "MAX_POSITION_EXPOSURE_PERCENT",
            5.0
        )
    )

    MAX_DAILY_LOSS_PERCENT = float(
        os.getenv(
            "MAX_DAILY_LOSS_PERCENT",
            5.0
        )
    )

    MAX_DAILY_TRADES = int(
        os.getenv(
            "MAX_DAILY_TRADES",
            20
        )
    )
    
    ATR_STOP_MULTIPLIER = float(
        os.getenv(
            "ATR_STOP_MULTIPLIER",
            1.0
        )
    )
    
    ATR_TAKE_PROFIT_MULTIPLIER = float(
        os.getenv(
            "ATR_TAKE_PROFIT_MULTIPLIER",
            3.0
        )
    )
    
    ATR_TRAILING_MULTIPLIER = float(
        os.getenv(
            "ATR_TRAILING_MULTIPLIER",
            2.0
        )
    )
    
    MIN_STRUCTURE_CANDLES = int(
        os.getenv(
            "MIN_STRUCTURE_CANDLES",
            6
        )
    )

    # =====================================================
    # EXECUTION
    # =====================================================

    ENABLE_PAPER_EXECUTION = (
        os.getenv(
            "ENABLE_PAPER_EXECUTION",
            "true"
        ).lower() == "true"
    )

    ENABLE_OPTIMIZER = (
        os.getenv(
            "ENABLE_OPTIMIZER",
            "false"
        ).lower() == "true"
    )

    ENABLE_MARKET_REGIME = (
        os.getenv(
            "ENABLE_MARKET_REGIME",
            "true"
        ).lower() == "true"
    )

    ENABLE_REPLAY = (
        os.getenv(
            "ENABLE_REPLAY",
            "false"
        ).lower() == "true"
    )

    # =====================================================
    # LOGGING
    # =====================================================

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO"
    )

    # =====================================================
    # MARKET
    # =====================================================

    SYMBOLS = [

        symbol.strip()

        for symbol in os.getenv(
            "SYMBOLS",
            "BTCUSDT,ETHUSDT,SOLUSDT"
        ).split(",")
    ]

    KLINE_INTERVAL = os.getenv(
        "KLINE_INTERVAL",
        "1m"
    )


settings = Settings()