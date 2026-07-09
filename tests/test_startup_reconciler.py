# -*- coding: utf-8 -*-

"""
Unit tests for core/services/startup_reconciler.py

Every Binance call is mocked (this sandbox has no network access to
Binance). Covers the three reconciliation scenarios documented in the
module's own docstring, plus the distinction between a confirmed
"order does not exist" (-2013) response -- the only case where an
automatic emergency close is safe -- and any other error, which must
only alert (CRITICAL) and never auto-close.
"""

import pytest

from unittest.mock import AsyncMock

from core.services.startup_reconciler import (
    reconcile_on_startup,
    DEFAULT_USER_ID
)

from core.services.binance_trading_client import (
    BinanceTradingError
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    Trade
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


@pytest.fixture(autouse=True)
def _cleanup_trades():

    yield

    session = SessionLocal()

    session.query(Trade).filter(
        Trade.symbol.like("RCTEST%")
    ).delete(
        synchronize_session=False
    )

    session.commit()

    session.close()


def _open_trade(symbol="RCTESTUSDT", order_list_id="123456"):

    return trades_repository.create_trade(
        user_id=DEFAULT_USER_ID,
        symbol=symbol,
        action="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0,
        trailing_stop=1.0,
        order_list_id=order_list_id
    )


def _client(**overrides):

    client = AsyncMock()

    client.get_open_orders.return_value = []

    for name, value in overrides.items():

        setattr(client, name, value)

    return client


class TestNoOpenTrades:

    @pytest.mark.asyncio
    async def test_no_open_trades_still_checks_orphan_orders(self):

        client = _client()

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        client.get_open_orders.assert_awaited_once_with(
            symbol="RCTESTUSDT"
        )


class TestScenarioOcoAlreadyDone:

    @pytest.mark.asyncio
    async def test_oco_all_done_closes_trade_as_reconciled(self):

        trade = _open_trade()

        client = _client()

        client.get_order_list_status.return_value = {
            "listOrderStatus": "ALL_DONE"
        }

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "CLOSED"
        assert refreshed.exit_reason == "RECONCILED_CLOSED"

    @pytest.mark.asyncio
    async def test_oco_still_executing_leaves_trade_open(self):

        trade = _open_trade()

        client = _client()

        client.get_order_list_status.return_value = {
            "listOrderStatus": "EXECUTING"
        }

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "OPEN"


class TestScenarioOcoMissing:

    @pytest.mark.asyncio
    async def test_order_not_found_triggers_emergency_close(self):

        trade = _open_trade()

        client = _client()

        client.get_order_list_status.side_effect = BinanceTradingError(
            "Order does not exist",
            binance_code=-2013
        )

        client.place_market_order.return_value = {"status": "FILLED"}

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        client.place_market_order.assert_awaited_once()

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "CLOSED"
        assert refreshed.exit_reason == "RECONCILED_EMERGENCY_CLOSE"

    @pytest.mark.asyncio
    async def test_unrelated_error_does_not_trigger_emergency_close(self):

        trade = _open_trade()

        client = _client()

        client.get_order_list_status.side_effect = BinanceTradingError(
            "Network error calling GET /api/v3/orderList: timeout"
        )

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        client.place_market_order.assert_not_awaited()

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "OPEN"

    @pytest.mark.asyncio
    async def test_generic_exception_does_not_trigger_emergency_close(self):

        trade = _open_trade()

        client = _client()

        client.get_order_list_status.side_effect = TimeoutError(
            "request timed out"
        )

        with pytest.raises(TimeoutError):

            await reconcile_on_startup(
                client,
                symbols=["RCTESTUSDT"]
            )

        client.place_market_order.assert_not_awaited()

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "OPEN"


class TestLegacyTradeWithoutOrderListId:

    @pytest.mark.asyncio
    async def test_missing_order_list_id_is_skipped_without_crashing(self):

        trade = _open_trade(order_list_id=None)

        client = _client()

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        client.get_order_list_status.assert_not_awaited()

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "OPEN"


class TestScenarioOrphanOrders:

    @pytest.mark.asyncio
    async def test_orphan_order_is_logged_and_not_touched(self):

        client = _client()

        client.get_open_orders.return_value = [
            {
                "symbol": "RCTESTUSDT",
                "orderId": 999,
                "orderListId": 555
            }
        ]

        # should not raise, and should not attempt to cancel/close
        # anything -- orphan orders are alert-only
        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        client.cancel_order.assert_not_awaited()
        client.cancel_order_list.assert_not_awaited()
        client.place_market_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_known_order_list_id_is_not_flagged_as_orphan(self):

        trade = _open_trade(order_list_id="777")

        client = _client()

        client.get_order_list_status.return_value = {
            "listOrderStatus": "EXECUTING"
        }

        client.get_open_orders.return_value = [
            {
                "symbol": "RCTESTUSDT",
                "orderId": 1,
                "orderListId": 777
            },
            {
                "symbol": "RCTESTUSDT",
                "orderId": 2,
                "orderListId": 777
            }
        ]

        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )

        refreshed = trades_repository.get_trade(trade.id)

        assert refreshed.status == "OPEN"

    @pytest.mark.asyncio
    async def test_open_orders_lookup_failure_is_non_fatal(self):

        client = _client()

        client.get_open_orders.side_effect = BinanceTradingError(
            "Network error"
        )

        # must not raise -- a lookup failure for orphan-order checking
        # should not block the rest of startup
        await reconcile_on_startup(
            client,
            symbols=["RCTESTUSDT"]
        )
