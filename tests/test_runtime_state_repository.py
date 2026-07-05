# -*- coding: utf-8 -*-

"""
Unit tests for data/storage/repositories/runtime_state_repository.py

This repository exists specifically to share MarketState telemetry
across OS process boundaries (API process vs. Runner process under
Full Stack) -- see core/state/market_state.py's
MarketState.from_persisted() and the module docstring here for the
full rationale.
"""

import pytest

from datetime import datetime

from data.storage.repositories.runtime_state_repository import (
    runtime_state_repository
)

from core.state.market_state import (
    MarketState
)


@pytest.fixture(autouse=True)
def _reset_runtime_state():

    runtime_state_repository.reset()

    yield


class TestGetWithNoData:

    def test_returns_none_when_never_flushed(self):

        assert runtime_state_repository.get() is None


class TestUpsert:

    def test_creates_row_on_first_upsert(self):

        state = MarketState()

        state.set_websocket_connected(True)

        state.register_kline("BTCUSDT")

        runtime_state_repository.upsert(
            state.snapshot()
        )

        persisted = runtime_state_repository.get()

        assert persisted is not None

        assert persisted["websocket_connected"] is True

        assert persisted["active_symbols"] == ["BTCUSDT"]

    def test_overwrites_existing_row_on_second_upsert(self):

        state = MarketState()

        state.set_websocket_connected(True)

        runtime_state_repository.upsert(
            state.snapshot()
        )

        state.set_websocket_connected(False)

        state.register_kline("ETHUSDT")

        runtime_state_repository.upsert(
            state.snapshot()
        )

        persisted = runtime_state_repository.get()

        assert persisted["websocket_connected"] is False

        assert persisted["active_symbols"] == ["ETHUSDT"]

        # confirms it's a single overwritten row, not an
        # accumulating history table
        from data.storage.database import SessionLocal
        from data.storage.models import RuntimeState

        session = SessionLocal()

        try:

            count = (
                session.query(RuntimeState).count()
            )

            assert count == 1

        finally:

            session.close()

    def test_persists_all_counters(self):

        state = MarketState()

        state.register_analysis_request()

        state.register_generated_signal()

        state.register_approved_signal()

        state.register_rejected_signal("LOW_CONFIDENCE")

        state.register_order_execution("EXECUTED")

        state.register_closed_position()

        runtime_state_repository.upsert(
            state.snapshot()
        )

        persisted = runtime_state_repository.get()

        assert persisted["total_analysis_requests"] == 1

        assert persisted["total_generated_signals"] == 1

        assert persisted["total_approved_signals"] == 1

        assert persisted["total_rejected_signals"] == 1

        assert persisted["total_executed_orders"] == 1

        assert persisted["total_closed_positions"] == 1

        assert persisted["blocked_signal_reasons"] == {
            "LOW_CONFIDENCE": 1
        }

        assert persisted["execution_reasons"] == {
            "EXECUTED": 1
        }

    def test_handles_empty_active_symbols(self):

        state = MarketState()

        runtime_state_repository.upsert(
            state.snapshot()
        )

        persisted = runtime_state_repository.get()

        assert persisted["active_symbols"] == []

    def test_preserves_started_at_timestamp(self):

        state = MarketState()

        runtime_state_repository.upsert(
            state.snapshot()
        )

        persisted = runtime_state_repository.get()

        assert isinstance(
            persisted["started_at"],
            datetime
        )


class TestReset:

    def test_clears_persisted_state(self):

        state = MarketState()

        runtime_state_repository.upsert(
            state.snapshot()
        )

        assert runtime_state_repository.get() is not None

        runtime_state_repository.reset()

        assert runtime_state_repository.get() is None


class TestCrossProcessSimulation:

    def test_persisted_state_reconstructs_into_working_snapshot(
        self
    ):

        """
        Simulates the real Full Stack scenario end to end: a
        "Runner" MarketState instance is mutated and flushed; a
        completely separate "API" MarketState.from_persisted() call
        reads it back and produces a snapshot with correct derived
        ratios -- without sharing the original Python object at all.
        """

        runner_state = MarketState()

        runner_state.set_websocket_connected(True)

        runner_state.register_kline("BTCUSDT")

        runner_state.register_analysis_request()

        runner_state.register_analysis_request()

        runner_state.register_generated_signal()

        runner_state.register_approved_signal()

        runner_state.register_order_execution()

        runtime_state_repository.upsert(
            runner_state.snapshot()
        )

        # this is a brand new object -- nothing is shared with
        # runner_state above except via the repository
        persisted = runtime_state_repository.get()

        api_side_state = MarketState.from_persisted(
            persisted
        )

        snapshot = api_side_state.snapshot()

        assert snapshot["websocket_connected"] is True

        assert snapshot["active_symbols"] == ["BTCUSDT"]

        assert snapshot["total_analysis_requests"] == 2

        assert snapshot["total_generated_signals"] == 1

        assert snapshot["signal_generation_ratio"] == 50.0

        assert snapshot["signal_approval_ratio"] == 100.0

        assert snapshot["execution_ratio"] == 100.0
