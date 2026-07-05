# -*- coding: utf-8 -*-

"""
Regression tests for core/state/market_state.py

Bug #1 fixed: data/ingestion/binance_ws.py calls market_state.register_kline(),
but MarketState only defined register_market_message(). This raised an
AttributeError on every closed candle received from the live Binance feed.

Bug #2 fixed: MarketState is an in-memory singleton, but apps/trader/runner.py
(which writes to it) and apps/api/main.py (which reads it for the
dashboard's /runtime endpoint) run as SEPARATE OS processes under Full
Stack (scripts/bootstrap/launcher.py). Without cross-process persistence,
the API's copy of market_state stays at its initial zeroed defaults
forever -- websocket_connected always False ("FEED DOWN" never clears),
active_symbols always empty, every signal/execution counter stuck at 0 --
regardless of how long the Runner has actually been operating. This is
why the dashboard could look "stuck" even while paper trading worked
correctly. Fixed by persisting MarketState to a shared database table
(see data/storage/repositories/runtime_state_repository.py) and giving
MarketState a from_persisted() classmethod to reconstruct a working
instance (with correctly recalculated ratios/uptime) from that
persisted dict.
"""

from datetime import datetime

from core.state.market_state import (
    MarketState
)


class TestRegisterKline:

    def test_register_kline_does_not_raise(self):

        state = MarketState()

        state.register_kline("BTCUSDT")

    def test_register_kline_updates_active_symbols(self):

        state = MarketState()

        state.register_kline("ETHUSDT")

        assert "ETHUSDT" in state.active_symbols

    def test_register_kline_increments_total_messages(self):

        state = MarketState()

        before = state.total_market_messages

        state.register_kline("BTCUSDT")

        assert state.total_market_messages == before + 1

    def test_register_kline_behaves_like_register_market_message(self):

        state_a = MarketState()

        state_b = MarketState()

        state_a.register_kline("BTCUSDT")

        state_b.register_market_message("BTCUSDT")

        assert (
            state_a.total_market_messages
            ==
            state_b.total_market_messages
        )

        assert (
            state_a.active_symbols
            ==
            state_b.active_symbols
        )


class TestFromPersisted:

    def test_reconstructs_websocket_connected(self):

        data = {
            "websocket_connected": True
        }

        instance = MarketState.from_persisted(data)

        assert instance.websocket_connected is True

    def test_reconstructs_active_symbols_as_set(self):

        data = {
            "active_symbols": ["BTCUSDT", "ETHUSDT"]
        }

        instance = MarketState.from_persisted(data)

        assert instance.active_symbols == {
            "BTCUSDT",
            "ETHUSDT"
        }

    def test_reconstructs_counters(self):

        data = {
            "total_analysis_requests": 10,
            "total_generated_signals": 5,
            "total_approved_signals": 3,
            "total_rejected_signals": 7,
            "total_executed_orders": 2,
            "total_closed_positions": 1
        }

        instance = MarketState.from_persisted(data)

        assert instance.total_analysis_requests == 10

        assert instance.total_generated_signals == 5

        assert instance.total_approved_signals == 3

        assert instance.total_rejected_signals == 7

        assert instance.total_executed_orders == 2

        assert instance.total_closed_positions == 1

    def test_reconstructs_reason_dicts(self):

        data = {
            "blocked_signal_reasons": {
                "LOW_CONFIDENCE": 4
            },
            "execution_reasons": {
                "EXECUTED": 2
            }
        }

        instance = MarketState.from_persisted(data)

        assert instance.get_blocked_signal_reasons() == {
            "LOW_CONFIDENCE": 4
        }

        assert instance.get_execution_reasons() == {
            "EXECUTED": 2
        }

    def test_missing_fields_default_safely(self):

        instance = MarketState.from_persisted({})

        snapshot = instance.snapshot()

        assert snapshot["websocket_connected"] is False

        assert snapshot["active_symbols"] == []

        assert snapshot["total_analysis_requests"] == 0

    def test_snapshot_recalculates_ratios_correctly(self):

        data = {
            "total_analysis_requests": 100,
            "total_generated_signals": 20,
            "total_approved_signals": 10,
            "total_executed_orders": 8
        }

        instance = MarketState.from_persisted(data)

        snapshot = instance.snapshot()

        assert snapshot["signal_generation_ratio"] == 20.0

        assert snapshot["signal_approval_ratio"] == 50.0

        assert snapshot["execution_ratio"] == 80.0

    def test_preserves_started_at_for_uptime_calculation(self):

        data = {
            "started_at": datetime(2026, 1, 1, 0, 0, 0)
        }

        instance = MarketState.from_persisted(data)

        snapshot = instance.snapshot()

        # uptime since 2026-01-01 must be a large positive number,
        # not the few-microseconds uptime of a freshly-constructed
        # MarketState() that ignored the persisted started_at
        assert snapshot["uptime_seconds"] > 1_000_000

    def test_none_started_at_falls_back_to_now(self):

        # defensive: a row that somehow has a null started_at must
        # not crash snapshot()'s uptime calculation
        data = {
            "started_at": None
        }

        instance = MarketState.from_persisted(data)

        snapshot = instance.snapshot()

        assert snapshot["uptime_seconds"] >= 0

    def test_does_not_mutate_input_dict(self):

        data = {
            "active_symbols": ["BTCUSDT"],
            "blocked_signal_reasons": {"X": 1}
        }

        MarketState.from_persisted(data)

        assert data["active_symbols"] == ["BTCUSDT"]

        assert data["blocked_signal_reasons"] == {"X": 1}
