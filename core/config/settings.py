# -*- coding: utf-8 -*-

import os


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

    BINANCE_API_KEY = os.getenv(
        "BINANCE_API_KEY",
        ""
    )

    BINANCE_SECRET_KEY = os.getenv(
        "BINANCE_SECRET_KEY",
        ""
    )

    # =====================================================
    # LOGGING
    # =====================================================

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO"
    )

    # =====================================================
    # SYMBOLS
    # =====================================================

    SYMBOLS = [
        symbol.strip()
        for symbol in os.getenv(
            "SYMBOLS",
            "BTCUSDT,ETHUSDT,SOLUSDT"
        ).split(",")
    ]


settings = Settings()