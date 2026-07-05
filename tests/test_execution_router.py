# -*- coding: utf-8 -*-

"""
Unit tests for core/services/execution_router.py

This is the single decision point between PAPER (simulated) and
LIVE (real Binance orders) execution -- see the module's own
docstring for the full reasoning behind the live execution sequence
and why an OCO failure after a successful entry is treated as the
single worst state this code can put a real account into.

Every Binance call is mocked (this sandbox has no network access to
Binance -- confirmed in earlier sessions). The scenarios here are
the ones that matter most for handling real money safely: a clean
success, a clean failure before anything is exposed, and the
unprotected-position emergency-close path in both its successful
and (worst case) unsuccessful outcomes.
"""

import pytest

from unittest.mock import patch

from core.services.execution_router import (
    ExecutionRouter
)

from core.services.binance_trading_client import (
    BinanceTradingClient,
    BinanceTradingError
)

from core.contracts.messages import (
    RiskDecisionPayload
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    Trade
)


def _make_payload(
    user_id,
    symbol="BTCUSDT",
    entry_price=100.0,
    quantity=1.0,
    stop_loss=95.0,
    take_profit=110.0,
    trailing_stop=1.0
):

    return RiskDecisionPayload(
        user_id=user_id,
        symbol=symbol,
        signal="BUY",
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        trailing_stop=trailing_stop
    )


@pytest.fixture(autouse=True)
def _cleanup_trades():

    yield

    session = SessionLocal()

    session.query(Trade).filter(
        Trade.user_id >= 999_000_000
    ).delete()

    session.commit()

    session.close()


class TestPaperExecution:

    def test_paper_execution_succeeds_and_records_trade(self):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_001
        )

        result = router._execute_paper(
            payload
        )

        assert result.success is True

        assert result.reason == "PAPER_FILLED"

        assert result.trade is not None

    def test_execute_routes_to_paper_when_mode_is_not_live(self):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_002
        )

        with patch(
            "core.services.execution_router.settings.MODE",
            "paper"
        ):

            import asyncio

            result = asyncio.run(
                router.execute(
                    payload
                )
            )

        assert result.reason == "PAPER_FILLED"


class TestMainnetSafetyLockThroughRouter:

    @pytest.mark.asyncio
    async def test_live_mainnet_without_confirmation_is_blocked(
        self
    ):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_003
        )

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                False
            ):

                with patch(
                    "core.services.execution_router."
                    "settings.LIVE_TRADING_CONFIRMED",
                    False
                ):

                    result = await router._execute_live(
                        payload
                    )

        assert result.success is False

        assert result.reason == "MAINNET_NOT_CONFIRMED"

    @pytest.mark.asyncio
    async def test_setting_mode_live_alone_does_not_bypass_the_lock(
        self
    ):

        # the exact scenario the lock exists for: someone sets
        # MODE=live and BINANCE_TESTNET=false in one edit, believing
        # they were configuring something else -- this single change
        # must never be enough to reach mainnet
        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_004
        )

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                False
            ):

                result = await router._execute_live(
                    payload
                )

        assert result.success is False

        assert result.reason == "MAINNET_NOT_CONFIRMED"


class TestLiveExecutionSuccess:

    @pytest.mark.asyncio
    async def test_uses_real_fill_price_not_requested_price(
        self
    ):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_005,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0
        )

        # real fill price (100.5) differs from the requested
        # entry_price (100.0) -- this is normal for MARKET orders
        entry_response = {
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.5"
        }

        async def fake_market_order(self, symbol, side, quantity):

            return entry_response

        async def fake_oco(self, **kwargs):

            return {"orderListId": 1}

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is True

        assert result.trade.entry_price == 100.5

        # stop_loss/take_profit must preserve the ORIGINAL risk
        # distance (5.0 / 10.0) relative to the REAL fill price,
        # not the originally requested levels
        assert result.trade.stop_loss == 95.5

        assert result.trade.take_profit == 110.5

    @pytest.mark.asyncio
    async def test_records_trade_only_after_both_orders_succeed(
        self
    ):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_006
        )

        entry_response = {
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.0"
        }

        async def fake_market_order(self, symbol, side, quantity):

            return entry_response

        async def fake_oco(self, **kwargs):

            return {"orderListId": 1}

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is True

        assert result.reason == "LIVE_FILLED"

        from data.storage.repositories.trades_repository import (
            trades_repository
        )

        open_trades = trades_repository.get_open_trades(
            user_id=999_000_006
        )

        assert len(open_trades) == 1


class TestLiveOrderTracking:

    """
    Bug fixed: place_market_order's and place_oco_sell_order's
    responses both already contained real Binance order identifiers
    (orderId / orderListId) but were discarded immediately after a
    successful call. Without persisting them, nothing downstream --
    most importantly core/agents/position_manager_agent.py's
    eventual LIVE exit handling -- has any way to cancel this
    trade's OCO or confirm its real fill state once it's time to
    close the position. See migration
    add_live_order_tracking_columns for the full rationale.
    """

    @pytest.mark.asyncio
    async def test_persists_entry_order_id_and_order_list_id(
        self
    ):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_007
        )

        entry_response = {
            "orderId": 555111,
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.0"
        }

        async def fake_market_order(self, symbol, side, quantity):

            return entry_response

        async def fake_oco(self, **kwargs):

            return {"orderListId": 777222}

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is True

        assert result.trade.entry_order_id == "555111"

        assert result.trade.order_list_id == "777222"

    @pytest.mark.asyncio
    async def test_paper_trades_never_get_a_real_order_id(
        self
    ):

        # PAPER never places a real order at all -- both columns
        # must stay NULL, never a placeholder value, so LIVE-only
        # reconciliation logic can tell "no real order to manage"
        # apart from "the id genuinely wasn't captured"
        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_008
        )

        result = await router.execute(
            payload
        )

        assert result.success is True

        assert result.trade.entry_order_id is None

        assert result.trade.order_list_id is None

    @pytest.mark.asyncio
    async def test_missing_order_list_id_in_oco_response_is_handled(
        self
    ):

        # defensive: an OCO response missing orderListId (malformed
        # or unexpected shape) must not crash execution -- it should
        # simply leave the column NULL rather than raising
        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_009
        )

        entry_response = {
            "orderId": 555112,
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.0"
        }

        async def fake_market_order(self, symbol, side, quantity):

            return entry_response

        async def fake_oco_missing_id(self, **kwargs):

            return {}

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco_missing_id
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is True

        assert result.trade.entry_order_id == "555112"

        assert result.trade.order_list_id is None


class TestLiveEntryFailure:

    @pytest.mark.asyncio
    async def test_entry_failure_rejects_cleanly_nothing_recorded(
        self
    ):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_007
        )

        async def fake_market_order_fails(
            self,
            symbol,
            side,
            quantity
        ):

            raise BinanceTradingError(
                "simulated insufficient balance"
            )

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order_fails
                ):

                    result = await router._execute_live(
                        payload
                    )

        assert result.success is False

        assert result.reason == "LIVE_ENTRY_FAILED"

        from data.storage.repositories.trades_repository import (
            trades_repository
        )

        open_trades = trades_repository.get_open_trades(
            user_id=999_000_007
        )

        assert open_trades == []

    @pytest.mark.asyncio
    async def test_entry_not_filled_rejects_without_oco_attempt(
        self
    ):

        # defensive: a response with executedQty=0 (e.g. the order
        # was accepted but never matched) must not proceed to
        # placing a protective OCO for a position that doesn't exist
        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_008
        )

        async def fake_market_order_unfilled(
            self,
            symbol,
            side,
            quantity
        ):

            return {
                "executedQty": "0",
                "cummulativeQuoteQty": "0"
            }

        oco_called = []

        async def fake_oco(self, **kwargs):

            oco_called.append(True)

            return {"orderListId": 1}

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order_unfilled
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is False

        assert result.reason == "LIVE_ENTRY_NOT_FILLED"

        assert oco_called == []


class TestUnprotectedPositionHandling:

    """
    The most safety-critical scenario this router handles: the
    entry succeeded (real money is now in a position) but the
    protective OCO failed to place. See the module docstring for
    why the response is an immediate market close, never a retry.
    """

    @pytest.mark.asyncio
    async def test_oco_failure_triggers_emergency_close(self):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_009
        )

        entry_response = {
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.0"
        }

        call_log = []

        async def fake_market_order(self, symbol, side, quantity):

            call_log.append(side)

            if side == "BUY":

                return entry_response

            return {
                "executedQty": str(quantity),
                "cummulativeQuoteQty": "99.0"
            }

        async def fake_oco_fails(self, **kwargs):

            raise BinanceTradingError(
                "simulated OCO rejection"
            )

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco_fails
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is False

        assert result.reason == "LIVE_OCO_FAILED_POSITION_CLOSED"

        # confirms the emergency close actually fired: BUY (entry)
        # then SELL (emergency close), not just BUY alone
        assert call_log == ["BUY", "SELL"]

    @pytest.mark.asyncio
    async def test_oco_failure_does_not_record_a_trade(self):

        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_010
        )

        entry_response = {
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.0"
        }

        async def fake_market_order(self, symbol, side, quantity):

            if side == "BUY":

                return entry_response

            return {
                "executedQty": str(quantity),
                "cummulativeQuoteQty": "99.0"
            }

        async def fake_oco_fails(self, **kwargs):

            raise BinanceTradingError(
                "simulated OCO rejection"
            )

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco_fails
                    ):

                        await router._execute_live(
                            payload
                        )

        from data.storage.repositories.trades_repository import (
            trades_repository
        )

        open_trades = trades_repository.get_open_trades(
            user_id=999_000_010
        )

        assert open_trades == []

    @pytest.mark.asyncio
    async def test_worst_case_oco_and_emergency_close_both_fail(
        self
    ):

        # the absolute worst case: a real, unprotected position is
        # left open with no further automated recourse -- this must
        # surface as a distinct, unmistakable reason rather than
        # being indistinguishable from a successfully-closed failure
        router = ExecutionRouter()

        payload = _make_payload(
            user_id=999_000_011
        )

        entry_response = {
            "executedQty": "1.0",
            "cummulativeQuoteQty": "100.0"
        }

        async def fake_market_order(self, symbol, side, quantity):

            if side == "BUY":

                return entry_response

            raise BinanceTradingError(
                "simulated network failure during emergency close"
            )

        async def fake_oco_fails(self, **kwargs):

            raise BinanceTradingError(
                "simulated OCO rejection"
            )

        with patch(
            "core.services.execution_router.settings.MODE",
            "live"
        ):

            with patch(
                "core.services.execution_router."
                "settings.BINANCE_TESTNET",
                True
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco_fails
                    ):

                        result = await router._execute_live(
                            payload
                        )

        assert result.success is False

        assert (
            result.reason
            == "LIVE_POSITION_UNPROTECTED_MANUAL_ACTION_REQUIRED"
        )

        # this reason must be distinct from the successfully-closed
        # case -- conflating them would hide the single most
        # dangerous outcome this module can produce
        assert (
            result.reason
            != "LIVE_OCO_FAILED_POSITION_CLOSED"
        )
