# -*- coding: utf-8 -*-

"""
Reads and writes the project's .env file safely for the Settings
panel in the frontend.

Design goals:
- Preserve comments, blank lines, and key order in .env when
  updating values (a naive os.environ dump would destroy all of
  that).
- Never return BINANCE_API_KEY / BINANCE_SECRET_KEY values back to
  the frontend once saved -- only whether a key is currently set
  (masked as a fixed-length placeholder), so secrets never round-trip
  through the browser after the initial save.
- MODE accepts "paper" or "live" (see core/services/execution_router.py
  and core/services/binance_trading_client.py for the real execution
  path). Switching to "live" here does NOT bypass
  LIVE_TRADING_CONFIRMED -- that remains a separate, deliberate .env
  setting enforced by BinanceTradingClient regardless of what MODE
  says. apps/api/main.py's PUT /settings endpoint also blocks any
  mode change while a real open position exists, and triggers a
  Runner restart afterward (see core/services/process_manager_service.py)
  since MODE is only read once, at process import time.
"""

import os

import re

from pathlib import Path

from typing import Optional


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

ENV_PATH = (
    PROJECT_ROOT
    / ".env"
)

# =====================================================
# KEYS MANAGED BY THE SETTINGS PANEL
# =====================================================
#
# Only these keys are editable through the Settings panel. Risk
# engine / market / execution flags are intentionally out of scope
# for this endpoint -- they're tuned via the optimizer and config
# files, not meant to be hand-edited by a non-technical user mid-run.

EDITABLE_KEYS = (
    "MODE",
    "BINANCE_TESTNET",
    "BINANCE_API_KEY",
    "BINANCE_SECRET_KEY",
    "LIVE_TRADING_CONFIRMED",
    "ACCOUNT_BALANCE",
    # Risk
    "RISK_PER_TRADE_PERCENT",
    "MAX_OPEN_POSITIONS",
    "MAX_POSITION_EXPOSURE_PERCENT",
    "MINIMUM_RISK_REWARD_RATIO",
    # Limits
    "MAX_DAILY_TRADES",
    "MAX_DAILY_LOSS_PERCENT",
    "MAXIMUM_DAILY_DRAWDOWN_PERCENT",
    "ENABLE_DAILY_TRADE_LIMIT",
    "ENABLE_DAILY_LOSS_LIMIT",
    "ENABLE_DRAWDOWN_PROTECTION",
    # Market
    "SYMBOLS",
    "KLINE_INTERVAL",
    # ATR / Multipliers
    "ATR_PERIOD",
    "ATR_STOP_MULTIPLIER",
    "ATR_TAKE_PROFIT_MULTIPLIER",
    "ATR_TRAILING_MULTIPLIER",
    "MINIMUM_ATR_PERCENT",
    # Signal quality
    "MINIMUM_SIGNAL_STRENGTH",
    "MIN_SIGNAL_CONFIDENCE",
    "ENABLE_VOLATILITY_FILTER",
    "ENABLE_EMA_TREND_FILTER",
    "ENABLE_MARKET_REGIME_ALIGNMENT",
    "ENABLE_SIGNAL_COOLDOWN",
    "SIGNAL_COOLDOWN_SECONDS",
    # Structure
    "STRUCTURE_MIN_SCORE",
    "STRUCTURE_MIN_IMPULSE_PERCENT",
    "STRUCTURE_ENABLE_CONSOLIDATION_FILTER",
    # Position management
    "ENABLE_TRAILING_STOP",
    "ENABLE_BREAKEVEN",
    "BREAKEVEN_TRIGGER_PERCENT",
    "ENABLE_DYNAMIC_TAKE_PROFIT",
    "DYNAMIC_TAKE_PROFIT_PROXIMITY_PERCENT",
    # Exchange
    "QUANTITY_PRECISION",
    "PRICE_PRECISION",
    "MIN_ORDER_QUANTITY",
    "MIN_ORDER_NOTIONAL",
    # Simulation (paper only)
    "ENABLE_FEE_SIMULATION",
    "ENABLE_SLIPPAGE_SIMULATION",
    "MAKER_FEE_PERCENT",
    "TAKER_FEE_PERCENT",
)

SECRET_KEYS = (
    "BINANCE_API_KEY",
    "BINANCE_SECRET_KEY"
)

# Modes the backend will actually accept. LIVE is deliberately
# excluded until real exchange order execution is implemented --
# adding it here is the only change needed to turn it on later.
ALLOWED_MODES = (
    "paper",
    "live",
)

MASK_PLACEHOLDER = "••••••••"


class SettingsValidationError(
    ValueError
):

    pass


# =====================================================
# LOW-LEVEL .ENV LINE PARSING
# =====================================================

_KEY_VALUE_PATTERN = re.compile(
    r"^(?P<key>[A-Z_][A-Z0-9_]*)=(?P<value>.*)$"
)


def _read_raw_lines():

    if not ENV_PATH.exists():

        return []

    with open(
        ENV_PATH,
        "r",
        encoding="utf-8",
        newline=""
    ) as f:

        return f.readlines()


def _write_raw_lines(lines):

    with open(
        ENV_PATH,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        f.writelines(lines)

    _restrict_env_file_permissions()


def _restrict_env_file_permissions():

    """
    Best-effort: restrict .env to owner-only read/write (chmod 600)
    after every write, since it holds real Binance API credentials.

    os.chmod's Unix permission bits don't carry the same meaning on
    Windows (which uses ACLs instead) -- this is a real no-op there,
    not a broken attempt, so it's wrapped to never fail the actual
    settings save over a platform difference that has no good
    equivalent action to take here anyway.
    """

    try:

        os.chmod(
            ENV_PATH,
            0o600
        )

    except OSError:

        pass


def _parse_current_values(lines):

    values = {}

    for line in lines:

        stripped = line.strip().lstrip(
            "\ufeff"
        )

        if (
            not stripped
            or stripped.startswith("#")
        ):

            continue

        match = _KEY_VALUE_PATTERN.match(
            stripped
        )

        if match:

            values[
                match.group("key")
            ] = match.group("value")

    return values


# =====================================================
# PUBLIC: GET CURRENT SETTINGS (MASKED)
# =====================================================

def get_settings():

    lines = _read_raw_lines()

    values = _parse_current_values(
        lines
    )

    def _bool(key, default="true"):
        return values.get(key, default).strip().lower() in ("1", "true", "yes", "on")

    def _float(key, default):
        try:
            return float(values.get(key, default))
        except (ValueError, TypeError):
            return float(default)

    def _int(key, default):
        try:
            return int(values.get(key, default))
        except (ValueError, TypeError):
            return int(default)

    def _str(key, default=""):
        return values.get(key, default).strip()

    mode = _str("MODE", "paper").lower()

    testnet_raw = values.get(
        "BINANCE_TESTNET",
        "true"
    ).strip().lower()

    api_key = values.get(
        "BINANCE_API_KEY",
        ""
    ).strip()

    secret_key = values.get(
        "BINANCE_SECRET_KEY",
        ""
    ).strip()

    live_trading_confirmed_raw = values.get(
        "LIVE_TRADING_CONFIRMED",
        "false"
    ).strip().lower()

    live_trading_confirmed = (
        live_trading_confirmed_raw
        in (
            "1",
            "true",
            "yes",
            "on"
        )
    )

    credentials_set = bool(
        api_key
    ) and bool(
        secret_key
    )

    live_trading_available = (
        credentials_set
        and live_trading_confirmed
    )

    if live_trading_available:

        live_trading_unavailable_reason = None

    elif not credentials_set:

        live_trading_unavailable_reason = (
            "Binance API key and secret must be set before "
            "switching to LIVE mode."
        )

    else:

        live_trading_unavailable_reason = (
            "LIVE_TRADING_CONFIRMED must be explicitly set to "
            "true in .env before switching to LIVE mode -- this "
            "is a deliberate second confirmation, separate from "
            "MODE and BINANCE_TESTNET, required before any real "
            "order can be placed."
        )

    return {
        "mode": mode,

        "allowed_modes": list(
            ALLOWED_MODES
        ),

        "binance_testnet": (
            testnet_raw
            in (
                "1",
                "true",
                "yes",
                "on"
            )
        ),

        "binance_api_key_set": bool(
            api_key
        ),

        "binance_secret_key_set": bool(
            secret_key
        ),

        "binance_api_key_masked": (
            MASK_PLACEHOLDER
            if api_key
            else ""
        ),

        "binance_secret_key_masked": (
            MASK_PLACEHOLDER
            if secret_key
            else ""
        ),

        "live_trading_available": live_trading_available,

        "live_trading_confirmed": live_trading_confirmed,

        "account_balance": _float("ACCOUNT_BALANCE", 10.0),

        "live_trading_unavailable_reason": (
            live_trading_unavailable_reason
        ),

        # =====================================================
        # RISK
        # =====================================================
        "risk_per_trade_percent":        _float("RISK_PER_TRADE_PERCENT", 1.0),
        "max_open_positions":            _int("MAX_OPEN_POSITIONS", 3),
        "max_position_exposure_percent": _float("MAX_POSITION_EXPOSURE_PERCENT", 25.0),
        "minimum_risk_reward_ratio":     _float("MINIMUM_RISK_REWARD_RATIO", 1.2),

        # =====================================================
        # DAILY LIMITS
        # =====================================================
        "max_daily_trades":               _int("MAX_DAILY_TRADES", 20),
        "max_daily_loss_percent":         _float("MAX_DAILY_LOSS_PERCENT", 5.0),
        "maximum_daily_drawdown_percent": _float("MAXIMUM_DAILY_DRAWDOWN_PERCENT", 5.0),
        "enable_daily_trade_limit":       _bool("ENABLE_DAILY_TRADE_LIMIT", "true"),
        "enable_daily_loss_limit":        _bool("ENABLE_DAILY_LOSS_LIMIT", "true"),
        "enable_drawdown_protection":     _bool("ENABLE_DRAWDOWN_PROTECTION", "true"),

        # =====================================================
        # MARKET
        # =====================================================
        "symbols":         _str("SYMBOLS", "BTCUSDT,ETHUSDT"),
        "kline_interval":  _str("KLINE_INTERVAL", "5m"),

        # =====================================================
        # ATR / MULTIPLIERS
        # =====================================================
        "atr_period":                _int("ATR_PERIOD", 14),
        "atr_stop_multiplier":       _float("ATR_STOP_MULTIPLIER", 1.0),
        "atr_take_profit_multiplier": _float("ATR_TAKE_PROFIT_MULTIPLIER", 2.0),
        "atr_trailing_multiplier":   _float("ATR_TRAILING_MULTIPLIER", 1.0),
        "minimum_atr_percent":       _float("MINIMUM_ATR_PERCENT", 0.01),

        # =====================================================
        # SIGNAL QUALITY
        # =====================================================
        "minimum_signal_strength":        _float("MINIMUM_SIGNAL_STRENGTH", 0.50),
        "min_signal_confidence":          _float("MIN_SIGNAL_CONFIDENCE", 0.45),
        "enable_volatility_filter":       _bool("ENABLE_VOLATILITY_FILTER", "true"),
        "enable_ema_trend_filter":        _bool("ENABLE_EMA_TREND_FILTER", "true"),
        "enable_market_regime_alignment": _bool("ENABLE_MARKET_REGIME_ALIGNMENT", "false"),
        "enable_signal_cooldown":         _bool("ENABLE_SIGNAL_COOLDOWN", "true"),
        "signal_cooldown_seconds":        _int("SIGNAL_COOLDOWN_SECONDS", 5),

        # =====================================================
        # MARKET STRUCTURE
        # =====================================================
        "structure_min_score":                  _float("STRUCTURE_MIN_SCORE", 2.0),
        "structure_min_impulse_percent":        _float("STRUCTURE_MIN_IMPULSE_PERCENT", 0.10),
        "structure_enable_consolidation_filter": _bool("STRUCTURE_ENABLE_CONSOLIDATION_FILTER", "true"),

        # =====================================================
        # POSITION MANAGEMENT
        # =====================================================
        "enable_trailing_stop":                _bool("ENABLE_TRAILING_STOP", "true"),
        "enable_breakeven":                    _bool("ENABLE_BREAKEVEN", "true"),
        "breakeven_trigger_percent":           _float("BREAKEVEN_TRIGGER_PERCENT", 0.50),
        "enable_dynamic_take_profit":          _bool("ENABLE_DYNAMIC_TAKE_PROFIT", "false"),
        "dynamic_take_profit_proximity_percent": _float("DYNAMIC_TAKE_PROFIT_PROXIMITY_PERCENT", 90.0),

        # =====================================================
        # EXCHANGE
        # =====================================================
        "quantity_precision":  _int("QUANTITY_PRECISION", 6),
        "price_precision":     _int("PRICE_PRECISION", 6),
        "min_order_quantity":  _float("MIN_ORDER_QUANTITY", 0.00001),
        "min_order_notional":  _float("MIN_ORDER_NOTIONAL", 0.0),

        # =====================================================
        # SIMULATION (paper only)
        # =====================================================
        "enable_fee_simulation":      _bool("ENABLE_FEE_SIMULATION", "true"),
        "enable_slippage_simulation": _bool("ENABLE_SLIPPAGE_SIMULATION", "true"),
        "maker_fee_percent":          _float("MAKER_FEE_PERCENT", 0.001),
        "taker_fee_percent":          _float("TAKER_FEE_PERCENT", 0.001),
    }


# =====================================================
# PUBLIC: UPDATE SETTINGS
# =====================================================

def update_settings(
    mode: Optional[str] = None,
    binance_testnet: Optional[bool] = None,
    binance_api_key: Optional[str] = None,
    binance_secret_key: Optional[str] = None,
    live_trading_confirmed: Optional[bool] = None,
    account_balance: Optional[float] = None,
    # Risk
    risk_per_trade_percent: Optional[float] = None,
    max_open_positions: Optional[int] = None,
    max_position_exposure_percent: Optional[float] = None,
    minimum_risk_reward_ratio: Optional[float] = None,
    # Daily limits
    max_daily_trades: Optional[int] = None,
    max_daily_loss_percent: Optional[float] = None,
    maximum_daily_drawdown_percent: Optional[float] = None,
    enable_daily_trade_limit: Optional[bool] = None,
    enable_daily_loss_limit: Optional[bool] = None,
    enable_drawdown_protection: Optional[bool] = None,
    # Market
    symbols: Optional[str] = None,
    kline_interval: Optional[str] = None,
    # ATR
    atr_period: Optional[int] = None,
    atr_stop_multiplier: Optional[float] = None,
    atr_take_profit_multiplier: Optional[float] = None,
    atr_trailing_multiplier: Optional[float] = None,
    minimum_atr_percent: Optional[float] = None,
    # Signal quality
    minimum_signal_strength: Optional[float] = None,
    min_signal_confidence: Optional[float] = None,
    enable_volatility_filter: Optional[bool] = None,
    enable_ema_trend_filter: Optional[bool] = None,
    enable_market_regime_alignment: Optional[bool] = None,
    enable_signal_cooldown: Optional[bool] = None,
    signal_cooldown_seconds: Optional[int] = None,
    # Structure
    structure_min_score: Optional[float] = None,
    structure_min_impulse_percent: Optional[float] = None,
    structure_enable_consolidation_filter: Optional[bool] = None,
    # Position management
    enable_trailing_stop: Optional[bool] = None,
    enable_breakeven: Optional[bool] = None,
    breakeven_trigger_percent: Optional[float] = None,
    enable_dynamic_take_profit: Optional[bool] = None,
    dynamic_take_profit_proximity_percent: Optional[float] = None,
    # Exchange
    quantity_precision: Optional[int] = None,
    price_precision: Optional[int] = None,
    min_order_quantity: Optional[float] = None,
    min_order_notional: Optional[float] = None,
    # Simulation
    enable_fee_simulation: Optional[bool] = None,
    enable_slippage_simulation: Optional[bool] = None,
    maker_fee_percent: Optional[float] = None,
    taker_fee_percent: Optional[float] = None,
):

    """
    Updates only the fields that are not None. Passing an empty
    string for an API key/secret clears it. Raises
    SettingsValidationError for invalid input -- callers (the API
    layer) are expected to translate that into a 400 response.
    """

    if mode is not None:

        normalized_mode = mode.strip().lower()

        if normalized_mode not in ALLOWED_MODES:

            raise SettingsValidationError(
                f"Invalid mode '{mode}'. "
                f"Allowed values: {', '.join(ALLOWED_MODES)}."
            )

    if (
        binance_api_key is not None
        and len(binance_api_key.strip()) not in (0, 64)
    ):

        raise SettingsValidationError(
            "BINANCE_API_KEY must be 64 characters "
            "(Binance API keys are 64-char hex strings), "
            "or empty to clear it."
        )

    if (
        binance_secret_key is not None
        and len(binance_secret_key.strip()) not in (0, 64)
    ):

        raise SettingsValidationError(
            "BINANCE_SECRET_KEY must be 64 characters "
            "(Binance API secrets are 64-char hex strings), "
            "or empty to clear it."
        )

    lines = _read_raw_lines()

    updates = {}

    def _b(v): return "true" if v else "false"

    if mode is not None:
        updates["MODE"] = mode.strip().lower()

    if binance_testnet is not None:
        updates["BINANCE_TESTNET"] = _b(binance_testnet)

    if binance_api_key is not None:
        updates["BINANCE_API_KEY"] = binance_api_key.strip()

    if binance_secret_key is not None:
        updates["BINANCE_SECRET_KEY"] = binance_secret_key.strip()

    if live_trading_confirmed is not None:
        updates["LIVE_TRADING_CONFIRMED"] = _b(live_trading_confirmed)

    if account_balance is not None:
        updates["ACCOUNT_BALANCE"] = str(account_balance)

    # Risk
    if risk_per_trade_percent is not None:
        updates["RISK_PER_TRADE_PERCENT"] = str(risk_per_trade_percent)
    if max_open_positions is not None:
        updates["MAX_OPEN_POSITIONS"] = str(max_open_positions)
    if max_position_exposure_percent is not None:
        updates["MAX_POSITION_EXPOSURE_PERCENT"] = str(max_position_exposure_percent)
    if minimum_risk_reward_ratio is not None:
        updates["MINIMUM_RISK_REWARD_RATIO"] = str(minimum_risk_reward_ratio)

    # Daily limits
    if max_daily_trades is not None:
        updates["MAX_DAILY_TRADES"] = str(max_daily_trades)
    if max_daily_loss_percent is not None:
        updates["MAX_DAILY_LOSS_PERCENT"] = str(max_daily_loss_percent)
    if maximum_daily_drawdown_percent is not None:
        updates["MAXIMUM_DAILY_DRAWDOWN_PERCENT"] = str(maximum_daily_drawdown_percent)
    if enable_daily_trade_limit is not None:
        updates["ENABLE_DAILY_TRADE_LIMIT"] = _b(enable_daily_trade_limit)
    if enable_daily_loss_limit is not None:
        updates["ENABLE_DAILY_LOSS_LIMIT"] = _b(enable_daily_loss_limit)
    if enable_drawdown_protection is not None:
        updates["ENABLE_DRAWDOWN_PROTECTION"] = _b(enable_drawdown_protection)

    # Market
    if symbols is not None:
        updates["SYMBOLS"] = symbols.strip()
    if kline_interval is not None:
        updates["KLINE_INTERVAL"] = kline_interval.strip()

    # ATR
    if atr_period is not None:
        updates["ATR_PERIOD"] = str(atr_period)
    if atr_stop_multiplier is not None:
        updates["ATR_STOP_MULTIPLIER"] = str(atr_stop_multiplier)
    if atr_take_profit_multiplier is not None:
        updates["ATR_TAKE_PROFIT_MULTIPLIER"] = str(atr_take_profit_multiplier)
    if atr_trailing_multiplier is not None:
        updates["ATR_TRAILING_MULTIPLIER"] = str(atr_trailing_multiplier)
    if minimum_atr_percent is not None:
        updates["MINIMUM_ATR_PERCENT"] = str(minimum_atr_percent)

    # Signal quality
    if minimum_signal_strength is not None:
        updates["MINIMUM_SIGNAL_STRENGTH"] = str(minimum_signal_strength)
    if min_signal_confidence is not None:
        updates["MIN_SIGNAL_CONFIDENCE"] = str(min_signal_confidence)
    if enable_volatility_filter is not None:
        updates["ENABLE_VOLATILITY_FILTER"] = _b(enable_volatility_filter)
    if enable_ema_trend_filter is not None:
        updates["ENABLE_EMA_TREND_FILTER"] = _b(enable_ema_trend_filter)
    if enable_market_regime_alignment is not None:
        updates["ENABLE_MARKET_REGIME_ALIGNMENT"] = _b(enable_market_regime_alignment)
    if enable_signal_cooldown is not None:
        updates["ENABLE_SIGNAL_COOLDOWN"] = _b(enable_signal_cooldown)
    if signal_cooldown_seconds is not None:
        updates["SIGNAL_COOLDOWN_SECONDS"] = str(signal_cooldown_seconds)

    # Structure
    if structure_min_score is not None:
        updates["STRUCTURE_MIN_SCORE"] = str(structure_min_score)
    if structure_min_impulse_percent is not None:
        updates["STRUCTURE_MIN_IMPULSE_PERCENT"] = str(structure_min_impulse_percent)
    if structure_enable_consolidation_filter is not None:
        updates["STRUCTURE_ENABLE_CONSOLIDATION_FILTER"] = _b(structure_enable_consolidation_filter)

    # Position management
    if enable_trailing_stop is not None:
        updates["ENABLE_TRAILING_STOP"] = _b(enable_trailing_stop)
    if enable_breakeven is not None:
        updates["ENABLE_BREAKEVEN"] = _b(enable_breakeven)
    if breakeven_trigger_percent is not None:
        updates["BREAKEVEN_TRIGGER_PERCENT"] = str(breakeven_trigger_percent)
    if enable_dynamic_take_profit is not None:
        updates["ENABLE_DYNAMIC_TAKE_PROFIT"] = _b(enable_dynamic_take_profit)
    if dynamic_take_profit_proximity_percent is not None:
        updates["DYNAMIC_TAKE_PROFIT_PROXIMITY_PERCENT"] = str(dynamic_take_profit_proximity_percent)

    # Exchange
    if quantity_precision is not None:
        updates["QUANTITY_PRECISION"] = str(quantity_precision)
    if price_precision is not None:
        updates["PRICE_PRECISION"] = str(price_precision)
    if min_order_quantity is not None:
        updates["MIN_ORDER_QUANTITY"] = str(min_order_quantity)
    if min_order_notional is not None:
        updates["MIN_ORDER_NOTIONAL"] = str(min_order_notional)

    # Simulation
    if enable_fee_simulation is not None:
        updates["ENABLE_FEE_SIMULATION"] = _b(enable_fee_simulation)
    if enable_slippage_simulation is not None:
        updates["ENABLE_SLIPPAGE_SIMULATION"] = _b(enable_slippage_simulation)
    if maker_fee_percent is not None:
        updates["MAKER_FEE_PERCENT"] = str(maker_fee_percent)
    if taker_fee_percent is not None:
        updates["TAKER_FEE_PERCENT"] = str(taker_fee_percent)

    new_lines, applied_keys = _apply_updates_to_lines(
        lines,
        updates
    )

    # any update targeting a key that didn't already exist in
    # the file gets appended at the end
    for key, value in updates.items():

        if key not in applied_keys:

            if new_lines and not new_lines[-1].endswith("\n"):

                new_lines.append("\n")

            new_lines.append(
                f"{key}={value}\n"
            )

    _write_raw_lines(
        new_lines
    )

    # keep the live process's in-memory environment consistent for
    # the remainder of this run (core/config/settings.py reads via
    # os.getenv at import time, so a full restart is still needed
    # for Settings.* class attributes to pick up the new value, but
    # os.environ itself should reflect reality immediately)
    for key, value in updates.items():

        os.environ[key] = value

    return get_settings()


def _apply_updates_to_lines(
    lines,
    updates
):

    remaining = dict(
        updates
    )

    new_lines = []

    applied_keys = set()

    for line in lines:

        stripped = line.strip()

        match = (
            _KEY_VALUE_PATTERN.match(
                stripped
            )
            if stripped and not stripped.startswith("#")
            else None
        )

        if match and match.group("key") in remaining:

            key = match.group("key")

            line_ending = (
                "\r\n"
                if line.endswith("\r\n")
                else "\n"
            )

            new_lines.append(
                f"{key}={remaining[key]}{line_ending}"
            )

            applied_keys.add(key)

        else:

            new_lines.append(line)

    return new_lines, applied_keys
