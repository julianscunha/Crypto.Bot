# -*- coding: utf-8 -*-

"""
core/services/startup_balance_service.py computes the "saldo mínimo
estimado" shown before starting the bot in LIVE mode. It used to call
core/services/exchange_filters.get_filters(), which only returns real
Binance minNotional/minQty data once the Runner has populated its
in-memory cache via load_filters() on its own LIVE startup -- a step
this check (which runs inside the API process) never triggers. That
silently understated the required balance to ~$0.00 for any symbol
whose min_notional the API process hadn't cached, which could let the
bot "pass" the startup check with a real balance far below Binance's
actual minimum order size. This test locks in the fix: the check must
fetch real filters itself instead of trusting that empty cache.
"""

from unittest.mock import AsyncMock, patch

import pytest

from core.config import settings_repository
from core.services.startup_balance_service import (
    build_startup_balance_report
)


@pytest.fixture(autouse=True)
def _live_symbol_settings():

    settings_repository.update_settings(
        mode="live",
        symbols="ETHUSDT",
        risk_per_trade_percent=1.0,
        max_position_exposure_percent=25.0,
        atr_stop_multiplier=1.0,
        minimum_atr_percent=0.01,
        min_order_quantity=0.0,
        min_order_notional=0.0,
        max_open_positions=1,
    )

    yield

    settings_repository.update_settings(
        mode="paper",
        symbols="BTCUSDT,ETHUSDT",
    )


@pytest.mark.asyncio
async def test_uses_real_min_notional_instead_of_empty_process_cache():

    """
    Binance's real ETHUSDT MIN_NOTIONAL/NOTIONAL filter is well above
    $0.00 (order of $5-20) -- if the required-balance math falls back
    to exchange_filters' empty-cache default (0.0) instead of fetching
    the real filter, a tiny account balance would incorrectly pass the
    startup check.
    """

    with patch(
        "core.services.startup_balance_service.BinanceTradingClient"
    ) as mock_client_cls:

        mock_client = mock_client_cls.return_value
        mock_client.get_account_info = AsyncMock(
            return_value={
                "balances": [
                    {"asset": "USDT", "free": "1.00"}
                ]
            }
        )
        mock_client.get_symbol_filters = AsyncMock(
            return_value={
                "min_notional": 20.0,
                "min_qty": 0.0001,
            }
        )
        mock_client.get_symbol_price = AsyncMock(
            return_value={"price": "3000.00"}
        )

        report = await build_startup_balance_report()

    assert report["current_balance"] == 1.0
    assert report["required_balance_single_trade"] >= 20.0
    assert report["allowed"] is False
    assert "$0.00" not in report["reason"]

    mock_client.get_symbol_filters.assert_awaited_once_with(
        "ETHUSDT"
    )
