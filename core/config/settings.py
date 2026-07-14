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
    default: int,
    minimum: int | None = None,
    maximum: int | None = None
) -> int:

    try:

        value = int(
            os.getenv(
                key,
                default
            )
        )

        if minimum is not None:

            value = max(
                value,
                minimum
            )

        if maximum is not None:

            value = min(
                value,
                maximum
            )

        return value

    except Exception:

        return default


def env_int_aliased(
    keys: tuple,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None
) -> int:

    """
    Like env_int, but accepts multiple possible env var names and
    uses the first one that's actually set, in order. Exists because
    this project ended up with more than one name representing the
    same setting in different places (STRUCTURE_MIN_CANDLES in
    market_structure_config.py, MINIMUM_STRUCTURE_CANDLES in
    trading_config.py) -- a person setting a third, equally
    reasonable variant (MIN_STRUCTURE_CANDLES) had it silently
    ignored, with every signal staying gated behind the 20-candle
    default with no error or warning anywhere.
    """

    for key in keys:

        if os.getenv(key) is not None:

            return env_int(
                key,
                default,
                minimum=minimum,
                maximum=maximum
            )

    return env_int(
        keys[0],
        default,
        minimum=minimum,
        maximum=maximum
    )


def env_float(
    key: str,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None
) -> float:

    try:

        value = float(
            os.getenv(
                key,
                default
            )
        )

        if minimum is not None:

            value = max(
                value,
                minimum
            )

        if maximum is not None:

            value = min(
                value,
                maximum
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
        "PAPER"
    ).upper()

    # =================================================
    # API
    # =================================================

    API_HOST = env_str(
        "API_HOST",
        "127.0.0.1"
    )

    API_PORT = env_int(

        "API_PORT",

        8000,

        minimum=1,

        maximum=65535
    )

    # Simple shared-secret auth (X-API-Token header) for mutating/
    # sensitive endpoints (PUT /settings, POST /runner/start,
    # POST /runner/stop) -- see apps/api/main.py's require_api_token
    # dependency. Empty/unset disables auth entirely, matching this
    # API's original localhost-only design (a warning is logged at
    # startup if the API is bound beyond localhost with no token set).
    API_ACCESS_TOKEN = env_str(
        "API_ACCESS_TOKEN",
        ""
    )

    # slowapi rate-limit spec (e.g. "10/minute") applied to the same
    # sensitive endpoints as API_ACCESS_TOKEN above. Configurable
    # mainly so the test suite can raise it well above what dozens of
    # sequential test requests would otherwise trip -- see
    # tests/conftest.py.
    API_RATE_LIMIT = env_str(
        "API_RATE_LIMIT",
        "10/minute"
    )

    # Comma-separated list of origins allowed by CORS (apps/api/main.py).
    # Defaults to the Vite dev server's two localhost variants -- the
    # only origins that mattered before Docker existed. Overriding
    # this is how the Docker-built frontend (served from nginx on a
    # different origin/port -- see docker-compose.yml) is allowed to
    # call this API from the browser. Deliberately NOT using
    # env_list() above -- it uppercases every value, which is correct
    # for ticker symbols but would corrupt a URL's scheme/host.
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    # =================================================
    # ALERTING
    # =================================================
    #
    # Generic webhook (POST, JSON body) for CRITICAL-severity events
    # -- see core/services/alert_service.py. Empty/unset disables
    # alerting; events still get logged locally regardless.
    WEBHOOK_ALERT_URL = env_str(
        "WEBHOOK_ALERT_URL",
        ""
    )

    # =================================================
    # LOGGING
    # =================================================
    #
    # Read by core/config/logging_config.py -- max size per log file
    # before it rotates + gzip-compresses, and how many compacted
    # (.gz) files to retain per log type before the oldest is
    # discarded. See core/utils/console_logger.py.
    MAX_LOG_FILE_SIZE = env_int(
        "MAX_LOG_FILE_SIZE",
        10_000_000,
        minimum=1
    )

    LOG_BACKUP_COUNT = env_int(
        "LOG_BACKUP_COUNT",
        5,
        minimum=0
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
    # LIVE TRADING SAFETY
    # =================================================
    #
    # Deliberately separate from MODE and BINANCE_TESTNET. A person
    # could set MODE=live and BINANCE_TESTNET=false in one .env edit
    # while believing they were still configuring testnet -- that
    # single edit must not be enough to enable real-money order
    # placement. This has to be set to true as its own, explicit
    # step. See core/services/binance_trading_client.py's
    # MainnetNotConfirmedError and core/services/execution_router.py
    # for where this is actually enforced.

    LIVE_TRADING_CONFIRMED = env_bool(
        "LIVE_TRADING_CONFIRMED",
        False
    )

    # =================================================
    # ACCOUNT
    # =================================================

    ACCOUNT_BALANCE = env_float(

        "ACCOUNT_BALANCE",

        100.0,

        minimum=1.0
    )

    # =================================================
    # RISK MANAGEMENT
    # =================================================

    RISK_PER_TRADE_PERCENT = env_float(

        "RISK_PER_TRADE_PERCENT",

        1.0,

        minimum=0.01,

        maximum=100.0
    )

    # =================================================
    # MAX_OPEN_POSITIONS
    # =================================================
    #
    # Accepts both names this setting has been written under: the
    # config that's actually enforced
    # (core/config/signal_quality_config.py's "maximum_open_positions",
    # checked by SignalQualityService._validate_position_limit) reads
    # MAXIMUM_OPEN_POSITIONS, but a person reasonably types
    # MAX_OPEN_POSITIONS (the name this very settings.py attribute
    # is called). Without this alias, setting MAX_OPEN_POSITIONS in
    # .env appeared to work (no error, the attribute exists) but had
    # zero effect on actual position-limit enforcement -- the real
    # check silently kept using its own 3-position default instead.

    MAX_OPEN_POSITIONS = env_int_aliased(

        (
            "MAX_OPEN_POSITIONS",

            "MAXIMUM_OPEN_POSITIONS"
        ),

        3,

        minimum=1
    )

    MAX_POSITION_EXPOSURE_PERCENT = env_float(

        "MAX_POSITION_EXPOSURE_PERCENT",

        25.0,

        minimum=0.1,

        maximum=100.0
    )

    MAX_DAILY_LOSS_PERCENT = env_float(

        "MAX_DAILY_LOSS_PERCENT",

        5.0,

        minimum=0.1,

        maximum=100.0
    )

    MAX_DAILY_TRADES = env_int(

        "MAX_DAILY_TRADES",

        20,

        minimum=1
    )

    MINIMUM_RISK_REWARD_RATIO = env_float(

        "MINIMUM_RISK_REWARD_RATIO",

        1.2,

        minimum=0.1
    )

    ATR_STOP_MULTIPLIER = env_float(

        "ATR_STOP_MULTIPLIER",

        1.0,

        minimum=0.1
    )

    ATR_TAKE_PROFIT_MULTIPLIER = env_float(

        "ATR_TAKE_PROFIT_MULTIPLIER",

        2.0,

        minimum=0.1
    )

    # =================================================
    # STRUCTURE
    # =================================================
    #
    # Accepts every name variant this setting has been written
    # under across this project's config files, plus a third,
    # equally reasonable name a person might type -- previously,
    # setting MIN_STRUCTURE_CANDLES in .env had no effect at all
    # because neither this nor STRUCTURE_MIN_CANDLES (below)
    # recognized it, and every signal stayed gated behind the
    # 20-candle default with no error or warning anywhere.

    MINIMUM_STRUCTURE_CANDLES = env_int_aliased(

        (
            "MINIMUM_STRUCTURE_CANDLES",

            "STRUCTURE_MIN_CANDLES",

            "MIN_STRUCTURE_CANDLES"
        ),

        20,

        minimum=5
    )

    # =================================================
    # STRATEGY
    # =================================================

    MINIMUM_SIGNAL_STRENGTH = env_float(

        "MINIMUM_SIGNAL_STRENGTH",

        0.50,

        minimum=0.01,

        maximum=1.0
    )

    # =================================================
    # TRADE MANAGEMENT
    # =================================================

    ENABLE_TRAILING_STOP = env_bool(
        "ENABLE_TRAILING_STOP",
        True
    )

    ENABLE_ATR_TRAILING = env_bool(
        "ENABLE_ATR_TRAILING",
        False
    )

    ATR_TRAILING_MULTIPLIER = env_float(

        "ATR_TRAILING_MULTIPLIER",

        1.0,

        minimum=0.1
    )

    ENABLE_BREAKEVEN = env_bool(
        "ENABLE_BREAKEVEN",
        True
    )

    BREAKEVEN_TRIGGER_PERCENT = env_float(

        "BREAKEVEN_TRIGGER_PERCENT",

        0.50,

        minimum=0.01,

        maximum=100.0
    )

    ENABLE_PARTIAL_TAKE_PROFIT = env_bool(
        "ENABLE_PARTIAL_TAKE_PROFIT",
        False
    )

    PARTIAL_TAKE_PROFIT_PERCENT = env_float(

        "PARTIAL_TAKE_PROFIT_PERCENT",

        50.0,

        minimum=1.0,

        maximum=100.0
    )

    ENABLE_DYNAMIC_TAKE_PROFIT = env_bool(
        "ENABLE_DYNAMIC_TAKE_PROFIT",
        False
    )

    ENABLE_VOLATILITY_BASED_MANAGEMENT = env_bool(
        "ENABLE_VOLATILITY_BASED_MANAGEMENT",
        False
    )

    # =================================================
    # SIGNAL QUALITY
    # =================================================

    MIN_SIGNAL_CONFIDENCE = env_float(

        "MIN_SIGNAL_CONFIDENCE",

        0.45,

        minimum=0.01,

        maximum=1.0
    )

    ENABLE_SIGNAL_COOLDOWN = env_bool(
        "ENABLE_SIGNAL_COOLDOWN",
        True
    )

    SIGNAL_COOLDOWN_SECONDS = env_int(

        "SIGNAL_COOLDOWN_SECONDS",

        5,

        minimum=0
    )

    ENABLE_EMA_TREND_FILTER = env_bool(
        "ENABLE_EMA_TREND_FILTER",
        True
    )

    EMA_FAST_PERIOD = env_int(

        "EMA_FAST_PERIOD",

        9,

        minimum=1
    )

    EMA_SLOW_PERIOD = env_int(

        "EMA_SLOW_PERIOD",

        21,

        minimum=2
    )

    MIN_TREND_STRENGTH_PERCENT = env_float(

        "MIN_TREND_STRENGTH_PERCENT",

        0.15,

        minimum=0.0
    )

    ENABLE_VOLATILITY_FILTER = env_bool(
        "ENABLE_VOLATILITY_FILTER",
        True
    )

    ATR_VALIDATION_PERIOD = env_int(

        "ATR_VALIDATION_PERIOD",

        14,

        minimum=1
    )

    MINIMUM_ATR_PERCENT = env_float(

        "MINIMUM_ATR_PERCENT",

        0.01,

        minimum=0.0
    )

    ENABLE_DRAWDOWN_PROTECTION = env_bool(
        "ENABLE_DRAWDOWN_PROTECTION",
        True
    )

    MAXIMUM_DAILY_DRAWDOWN_PERCENT = env_float(

        "MAXIMUM_DAILY_DRAWDOWN_PERCENT",

        5.0,

        minimum=0.1,

        maximum=100.0
    )

    # =================================================
    # MARKET STRUCTURE
    # =================================================

    STRUCTURE_MAX_PRICE_HISTORY = env_int(

        "STRUCTURE_MAX_PRICE_HISTORY",

        300,

        minimum=50
    )

    STRUCTURE_SWING_WINDOW = env_int(

        "STRUCTURE_SWING_WINDOW",

        2,

        minimum=1
    )

    STRUCTURE_MIN_REQUIRED_SWINGS = env_int(

        "STRUCTURE_MIN_REQUIRED_SWINGS",

        2,

        minimum=1
    )

    # =================================================
    # STRUCTURE_MIN_CANDLES
    # =================================================
    #
    # See MINIMUM_STRUCTURE_CANDLES above for the full explanation
    # -- both settings represent the same underlying concept and
    # must accept the same name variants so a person configuring
    # one doesn't unknowingly miss the other.

    STRUCTURE_MIN_CANDLES = env_int_aliased(

        (
            "STRUCTURE_MIN_CANDLES",

            "MINIMUM_STRUCTURE_CANDLES",

            "MIN_STRUCTURE_CANDLES"
        ),

        20,

        minimum=5
    )

    STRUCTURE_MIN_SCORE = env_float(

        "STRUCTURE_MIN_SCORE",

        2.0,

        minimum=0.1
    )

    STRUCTURE_MIN_IMPULSE_WINDOW = env_int(

        "STRUCTURE_MIN_IMPULSE_WINDOW",

        5,

        minimum=2
    )

    STRUCTURE_MIN_IMPULSE_PERCENT = env_float(

        "STRUCTURE_MIN_IMPULSE_PERCENT",

        0.10,

        minimum=0.0
    )

    STRUCTURE_IMPULSE_SCORE = env_float(

        "STRUCTURE_IMPULSE_SCORE",

        1.0,

        minimum=0.1
    )

    STRUCTURE_BULLISH_HIGH_SCORE = env_float(

        "STRUCTURE_BULLISH_HIGH_SCORE",

        1.0,

        minimum=0.1
    )

    STRUCTURE_BULLISH_LOW_SCORE = env_float(

        "STRUCTURE_BULLISH_LOW_SCORE",

        1.0,

        minimum=0.1
    )

    STRUCTURE_ENABLE_CONSOLIDATION_FILTER = env_bool(
        "STRUCTURE_ENABLE_CONSOLIDATION_FILTER",
        True
    )

    STRUCTURE_MIN_CONSOLIDATION_WINDOW = env_int(

        "STRUCTURE_MIN_CONSOLIDATION_WINDOW",

        10,

        minimum=2
    )

    STRUCTURE_MAX_CONSOLIDATION_RANGE = env_float(

        "STRUCTURE_MAX_CONSOLIDATION_RANGE",

        0.30,

        minimum=0.01
    )

    STRUCTURE_ENABLE_FAKE_BREAKOUT_FILTER = env_bool(
        "STRUCTURE_ENABLE_FAKE_BREAKOUT_FILTER",
        False
    )

    STRUCTURE_MIN_BREAKOUT_DISTANCE_PERCENT = env_float(

        "STRUCTURE_MIN_BREAKOUT_DISTANCE_PERCENT",

        0.20,

        minimum=0.0
    )

    STRUCTURE_REQUIRE_BOS_CONFIRMATION = env_bool(
        "STRUCTURE_REQUIRE_BOS_CONFIRMATION",
        False
    )

    STRUCTURE_ENABLE_REGIME_AWARE = env_bool(
        "STRUCTURE_ENABLE_REGIME_AWARE",
        False
    )

    STRUCTURE_ENABLE_ADAPTIVE_THRESHOLDS = env_bool(
        "STRUCTURE_ENABLE_ADAPTIVE_THRESHOLDS",
        False
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
        False
    )

    ENABLE_REPLAY = env_bool(
        "ENABLE_REPLAY",
        False
    )

    # =================================================
    # EXCHANGE PRECISION
    # =================================================
    #
    # Read by core/config/exchange_config.py. Used to round
    # ATR-based stop_loss/take_profit in RiskAgent -- was never
    # actually wired to this Settings class before (exchange_config.py
    # did getattr(settings, "PRICE_PRECISION", 2), but this attribute
    # never existed here, so any .env value was silently ignored and
    # it was always the hardcoded default of 2). For low-priced
    # symbols (e.g. DOGEUSDT, price ~$0.08) that fallback of 2
    # decimals is coarser than a realistic ATR-based stop distance --
    # stop_loss and take_profit round to the same value as entry
    # price, and RiskAgent rejects every single signal as
    # INVALID_RISK_LEVELS. 6 decimals covers sub-$1 assets while still
    # being a sane default for higher-priced ones.
    PRICE_PRECISION = env_int(
        "PRICE_PRECISION",
        6,
        minimum=0
    )

    # =================================================
    # LOGGING
    # =================================================

    LOG_LEVEL = env_str(
        "LOG_LEVEL",
        "INFO"
    ).upper()

    # =================================================
    # MARKET
    # =================================================

    SYMBOLS = env_list(

        "SYMBOLS",

        "BTCUSDT,ETHUSDT"
    )

    KLINE_INTERVAL = env_str(
        "KLINE_INTERVAL",
        "5m"
    )


settings = (
    Settings()
)
