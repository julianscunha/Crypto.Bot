# -*- coding: utf-8 -*-

"""
Cache de filtros de exchange por símbolo (LOT_SIZE, PRICE_FILTER).

Carregado no startup do runner em modo LIVE e consultado pelo
RiskAgent e BinanceTradingClient para formatar quantity e preços.

Em modo PAPER ou se a busca falhar, usa defaults conservadores.
"""

from core.utils.console_logger import log


# Defaults conservadores quando não há dado real
_DEFAULTS = {
    "qty_precision":   4,
    "min_qty":         0.0001,
    "price_precision": 2,
    "tick_size":       0.01,
    "min_notional":    0.0,
}

# Cache em memória: { "BTCUSDT": { qty_precision, price_precision, ... } }
_cache: dict = {}


def get_filters(
    symbol: str
) -> dict:

    return _cache.get(
        symbol,
        _DEFAULTS
    )


def format_quantity(
    symbol: str,
    quantity: float
) -> str:

    f = get_filters(symbol)
    prec = f["qty_precision"]

    # Arredondar para o step size
    tick = 10 ** (-prec) if prec > 0 else 1
    rounded = round(
        int(quantity / tick) * tick,
        prec
    )

    if prec == 0:
        return str(int(rounded))

    return f"{rounded:.{prec}f}"


def format_price(
    symbol: str,
    price: float
) -> str:

    f = get_filters(symbol)
    prec = f["price_precision"]

    # Arredondar para o tick size
    tick = f["tick_size"]
    if tick > 0:
        rounded = round(round(price / tick) * tick, prec)
    else:
        rounded = round(price, prec)

    return f"{rounded:.{prec}f}"


async def load_filters(
    client,
    symbols: list
):

    """
    Busca filtros reais da Binance para cada símbolo e popula o cache.
    Chamado no startup do runner em modo LIVE.
    """

    for symbol in symbols:

        try:

            filters = await client.get_symbol_filters(symbol)

            if filters:

                _cache[symbol] = {
                    **_DEFAULTS,
                    **filters
                }

                log(
                    "SYSTEM",
                    (
                        f"FILTERS {symbol}: "
                        f"qty_prec={_cache[symbol]['qty_precision']} "
                        f"price_prec={_cache[symbol]['price_precision']} "
                        f"min_qty={_cache[symbol]['min_qty']} "
                        f"min_notional={_cache[symbol]['min_notional']}"
                    )
                )

        except Exception as error:

            log(
                "SYSTEM",
                (
                    f"FILTERS {symbol}: falha ao buscar — "
                    f"usando defaults ({error})"
                ),
                "WARNING"
            )

            _cache[symbol] = dict(_DEFAULTS)


# Saldo real da Binance — populado no startup LIVE
_live_balance: float | None = None


def set_live_balance(balance: float):
    global _live_balance
    _live_balance = balance


def get_account_balance(configured_balance: float) -> float:
    """
    Em modo LIVE retorna o saldo real da Binance.
    Em modo PAPER retorna o saldo configurado no .env.
    """
    if _live_balance is not None:
        return _live_balance
    return configured_balance
