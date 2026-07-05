# -*- coding: utf-8 -*-

"""
Saldo em runtime — populado no startup do runner com o valor
real da Binance (modo LIVE) ou com o valor do .env (modo PAPER).

Nunca sobrescreve o .env. O RiskAgent lê daqui.
"""

_balance: float | None = None


def set_balance(value: float) -> None:
    global _balance
    _balance = value


def get_balance(fallback: float = 0.0) -> float:
    return _balance if _balance is not None else fallback
