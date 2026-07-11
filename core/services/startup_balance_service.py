# -*- coding: utf-8 -*-

from __future__ import annotations

from core.config.settings_repository import (
    get_settings,
    _read_raw_lines,
    _parse_current_values,
)
from core.services.binance_trading_client import BinanceTradingClient
from core.services.exchange_filters import get_filters


def _parse_symbols(raw: str) -> list[str]:

    return [
        symbol.strip().upper()
        for symbol in (raw or "").split(",")
        if symbol.strip()
    ]


def _float(value, fallback: float = 0.0) -> float:

    try:
        return float(value)
    except Exception:
        return fallback


def _int(value, fallback: int = 0) -> int:

    try:
        return int(value)
    except Exception:
        return fallback


async def _fetch_live_balance_and_source() -> tuple[float | None, str, str | None]:

    raw_env = _parse_current_values(_read_raw_lines())

    api_key = raw_env.get("BINANCE_API_KEY", "").strip()
    api_secret = raw_env.get("BINANCE_SECRET_KEY", "").strip()
    testnet = raw_env.get("BINANCE_TESTNET", "true").strip().lower() in ("1", "true", "yes", "on")
    confirmed = raw_env.get("LIVE_TRADING_CONFIRMED", "false").strip().lower() in ("1", "true", "yes", "on")

    client = BinanceTradingClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
        live_trading_confirmed=confirmed
    )

    account = await client.get_account_info()

    balance = next(
        (float(item["free"]) for item in account.get("balances", []) if item.get("asset") == "USDT"),
        None
    )

    source = "binance_testnet" if testnet else "binance_mainnet"
    return balance, source, None


async def build_startup_balance_report() -> dict:

    settings = get_settings()
    symbols = _parse_symbols(settings.get("symbols", ""))
    if not symbols:
        return {
            "allowed": True,
            "current_balance": _float(settings.get("account_balance", 0.0)),
            "source": "paper",
            "symbols": [],
            "required_balance_single_trade": 0.0,
            "required_balance_max_positions": 0.0,
            "shortfall": 0.0,
            "reason": None,
        }

    mode = str(settings.get("mode", "paper")).lower()
    current_balance = _float(settings.get("account_balance", 0.0))
    source = "paper"
    error = None

    if mode == "live":
        try:
            live_balance, source, error = await _fetch_live_balance_and_source()
            if live_balance is not None:
                current_balance = live_balance
        except Exception as exc:
            error = str(exc)

    risk_percent = max(_float(settings.get("risk_per_trade_percent", 0.25)), 0.0001)
    max_exposure_percent = max(_float(settings.get("max_position_exposure_percent", 100.0)), 0.0001)
    atr_stop_multiplier = max(_float(settings.get("atr_stop_multiplier", 2.0)), 0.0001)
    minimum_atr_percent = max(_float(settings.get("minimum_atr_percent", 0.0)), 0.0)
    min_order_notional_default = max(_float(settings.get("min_order_notional", 0.0)), 0.0)
    min_order_quantity_default = max(_float(settings.get("min_order_quantity", 0.0)), 0.0)
    max_open_positions = max(_int(settings.get("max_open_positions", 1)), 1)

    symbol_rows = []
    required_single_trade = 0.0

    for symbol in symbols:
        price_client = BinanceTradingClient(
            api_key="",
            api_secret="",
            testnet=(mode == "live" and source == "binance_testnet"),
            live_trading_confirmed=True
        )

        # get_filters() only returns real data once the Runner has
        # populated exchange_filters._cache via load_filters() on its
        # own LIVE startup -- this check runs from the API process,
        # which never calls that, so it silently fell back to
        # min_notional=0.0 and understated the real minimum required
        # balance. Fetch the real filters directly (same public,
        # unsigned exchangeInfo endpoint used by price_client below)
        # instead of trusting a cache this process never fills.
        try:
            filters = await price_client.get_symbol_filters(symbol)
        except Exception:
            filters = get_filters(symbol)

        min_notional = max(
            min_order_notional_default,
            _float(filters.get("min_notional", 0.0))
        )
        min_qty = max(
            min_order_quantity_default,
            _float(filters.get("min_qty", 0.0))
        )

        price = 0.0
        try:
            ticker = await price_client.get_symbol_price(symbol)
            price = _float(ticker.get("price", 0.0))
        except Exception as exc:
            error = error or f"Falha ao consultar preço de {symbol}: {exc}"

        balance_for_min_notional = 0.0
        balance_for_min_qty = 0.0
        balance_for_exposure = 0.0

        if minimum_atr_percent > 0:
            balance_for_min_notional = (
                min_notional
                * atr_stop_multiplier
                * minimum_atr_percent
                / risk_percent
            )

            if price > 0:
                balance_for_min_qty = (
                    min_qty
                    * price
                    * atr_stop_multiplier
                    * minimum_atr_percent
                    / risk_percent
                )

        if max_exposure_percent > 0:
            balance_for_exposure = (
                min_notional
                * 100
                / max_exposure_percent
            )

        symbol_required = max(
            balance_for_min_notional,
            balance_for_min_qty,
            balance_for_exposure,
            min_notional
        )

        required_single_trade = max(required_single_trade, symbol_required)

        symbol_rows.append({
            "symbol": symbol,
            "price": round(price, 8) if price > 0 else None,
            "min_notional": round(min_notional, 8),
            "min_qty": round(min_qty, 8),
            "required_balance": round(symbol_required, 8),
        })

    required_max_positions = required_single_trade * min(max_open_positions, len(symbols))
    shortfall = max(required_single_trade - current_balance, 0.0)
    allowed = current_balance >= required_single_trade and error is None

    reason = None
    if not allowed:
        if error:
            reason = error
        else:
            worst = max(symbol_rows, key=lambda row: row["required_balance"])
            reason = (
                f"Saldo insuficiente para os pares selecionados. "
                f"Minimum estimado para um trade: ${required_single_trade:.2f} "
                f"(par mais exigente: {worst['symbol']})."
            )

    return {
        "allowed": allowed,
        "current_balance": round(current_balance, 2),
        "source": source,
        "symbols": symbol_rows,
        "required_balance_single_trade": round(required_single_trade, 2),
        "required_balance_max_positions": round(required_max_positions, 2),
        "shortfall": round(shortfall, 2),
        "reason": reason,
    }
