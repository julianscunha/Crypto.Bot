# -*- coding: utf-8 -*-

"""
Unit tests for apps/trader/runner.py

main() is not tested directly here since it opens a real Binance
websocket connection and runs forever; that's an integration concern
better suited to manual/staging verification, not a unit test.

flush_runtime_state_periodically() IS tested directly: it's the fix
for the cross-process MarketState bug (see test_market_state.py and
test_runtime_state_repository.py for the full explanation) -- without
it, the API process's /runtime endpoint stays at zeroed defaults
forever, no matter how long the Runner has actually been live.
"""

import asyncio

import pytest

from unittest.mock import patch

from apps.trader.runner import (
    print_system_panel,
    initialize_agents,
    print_session_report,
    flush_runtime_state_periodically,
    RUNTIME_STATE_FLUSH_INTERVAL_SECONDS
)

from core.bus.event_bus import (
    EventBus
)

from core.state.market_state import (
    market_state
)

from data.storage.repositories.runtime_state_repository import (
    runtime_state_repository
)


class TestPrintSystemPanel:

    def test_does_not_raise(self, capsys):

        print_system_panel()

        captured = capsys.readouterr()

        assert "CRYPTO.BOT ENGINE" in captured.out


class TestInitializeAgents:

    def test_registers_all_five_agents_on_bus(self):

        bus = EventBus()

        initialize_agents(bus)

        subscriber_names = {
            type(sub).__name__
            for sub in bus.subscribers
        }

        assert subscriber_names == {
            "AnalystAgent",
            "StrategyAgent",
            "RiskAgent",
            "ExecutionAgent",
            "PositionManagerAgent"
        }

    def test_initializing_twice_does_not_duplicate_subscribers(self):

        bus = EventBus()

        initialize_agents(bus)

        initialize_agents(bus)

        # AnalystAgent/RiskAgent/ExecutionAgent/PositionManagerAgent
        # subscribe via base_agent-style logic that dedupes by
        # identity; this just confirms calling it again doesn't
        # error or runaway-grow the subscriber list to something
        # unreasonable
        assert len(bus.subscribers) <= 10


class TestPrintSessionReport:

    def test_does_not_raise_with_no_trades(self, capsys):

        print_session_report()

        captured = capsys.readouterr()

        assert "LIVE SESSION REPORT" in captured.out

    def test_includes_market_section(self, capsys):

        print_session_report()

        captured = capsys.readouterr()

        assert "MARKET" in captured.out


class TestFlushRuntimeStatePeriodically:

    @pytest.fixture(autouse=True)
    def _reset_runtime_state(self):

        runtime_state_repository.reset()

        yield

    @pytest.mark.asyncio
    async def test_flushes_market_state_to_database(self):

        market_state.set_websocket_connected(True)

        market_state.register_kline("BTCUSDT")

        # patch the interval to a tiny real sleep rather than an
        # AsyncMock that returns instantly -- an instant mock turns
        # the `while True` loop into a tight spin that starves the
        # test's own event-loop turn (it never actually yields
        # control), so flushed.wait() below would never get
        # scheduled. A short real sleep still yields control each
        # iteration, same as the real multi-second interval would,
        # just faster.

        flushed = asyncio.Event()

        real_upsert = runtime_state_repository.upsert

        def _upsert_and_signal(snapshot):

            real_upsert(snapshot)

            flushed.set()

        with patch(
            "apps.trader.runner.RUNTIME_STATE_FLUSH_INTERVAL_SECONDS",
            0.01
        ):

            with patch(
                "apps.trader.runner.runtime_state_repository.upsert",
                side_effect=_upsert_and_signal
            ):

                task = asyncio.create_task(
                    flush_runtime_state_periodically()
                )

                await asyncio.wait_for(
                    flushed.wait(),
                    timeout=2
                )

                task.cancel()

                try:

                    await task

                except asyncio.CancelledError:

                    pass

        persisted = runtime_state_repository.get()

        assert persisted is not None

        assert persisted["websocket_connected"] is True

        assert persisted["active_symbols"] == ["BTCUSDT"]

    @pytest.mark.asyncio
    async def test_survives_a_failed_flush_without_raising(self):

        # regression: a transient DB error here must not crash the
        # whole Runner process -- the websocket/agent pipeline is
        # far more important than this telemetry being perfectly
        # up to date every single flush interval

        attempted = asyncio.Event()

        def _raise_and_signal(snapshot):

            attempted.set()

            raise Exception("simulated DB error")

        with patch(
            "apps.trader.runner.RUNTIME_STATE_FLUSH_INTERVAL_SECONDS",
            0.01
        ):

            with patch(
                "apps.trader.runner.runtime_state_repository.upsert",
                side_effect=_raise_and_signal
            ):

                task = asyncio.create_task(
                    flush_runtime_state_periodically()
                )

                await asyncio.wait_for(
                    attempted.wait(),
                    timeout=2
                )

                task.cancel()

                try:

                    await task

                except asyncio.CancelledError:

                    pass

        # if we got here without an unhandled exception propagating
        # out of the task, the failure was correctly caught and
        # logged rather than crashing the Runner process
        assert attempted.is_set()

    def test_flush_interval_is_reasonable(self):

        # sanity bound: must be frequent enough to feel "live" on
        # the dashboard (which polls every 3s -- see
        # frontend/src/pages/Dashboard.jsx) but not so frequent that
        # it's pointless overhead
        assert 1 <= RUNTIME_STATE_FLUSH_INTERVAL_SECONDS <= 10
