# -*- coding: utf-8 -*-

"""
Unit tests for core/agents/execution_agent.py's _validate_execution,
isolated from the full pipeline (tests/test_pipeline_integration.py
only exercises the happy path end to end via the whole bus).

Covers the branches not exercised elsewhere: INVALID_ENTRY_PRICE,
INVALID_POSITION_SIZE, and the tenant/symbol boundary branches
(INVALID_USER_ID, SYMBOL_NOT_ALLOWED).
"""

import pytest

from core.agents.execution_agent import ExecutionAgent

from core.contracts.messages import RiskDecisionPayload

from core.bus.event_bus import EventBus


def _make_payload(
    user_id=700,
    symbol="BTCUSDT",
    signal="BUY",
    entry_price=100.0,
    quantity=1.0,
    stop_loss=95.0,
    take_profit=110.0,
    trailing_stop=1.0
):

    return RiskDecisionPayload(
        user_id=user_id,
        symbol=symbol,
        signal=signal,
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        trailing_stop=trailing_stop
    )


@pytest.fixture
def agent():

    return ExecutionAgent(EventBus())


class TestValidateExecution:

    def test_invalid_entry_price_when_zero_or_negative(
        self,
        agent
    ):

        payload = _make_payload(
            entry_price=0.0
        )

        valid, reason = agent._validate_execution(payload)

        assert valid is False

        assert reason == "INVALID_ENTRY_PRICE"

    def test_invalid_position_size_when_zero_or_negative(
        self,
        agent
    ):

        payload = _make_payload(
            quantity=0.0
        )

        valid, reason = agent._validate_execution(payload)

        assert valid is False

        assert reason == "INVALID_POSITION_SIZE"

    def test_invalid_user_id_when_not_an_int(
        self,
        agent
    ):

        payload = _make_payload(
            user_id="not-an-int"
        )

        valid, reason = agent._validate_execution(payload)

        assert valid is False

        assert reason == "INVALID_USER_ID"

    def test_invalid_user_id_when_negative(
        self,
        agent
    ):

        payload = _make_payload(
            user_id=-1
        )

        valid, reason = agent._validate_execution(payload)

        assert valid is False

        assert reason == "INVALID_USER_ID"

    def test_symbol_not_allowed_when_outside_settings_symbols(
        self,
        agent
    ):

        payload = _make_payload(
            symbol="DOGEUSDT"
        )

        valid, reason = agent._validate_execution(payload)

        assert valid is False

        assert reason == "SYMBOL_NOT_ALLOWED"

    def test_valid_payload_passes(
        self,
        agent
    ):

        payload = _make_payload()

        valid, reason = agent._validate_execution(payload)

        assert valid is True

        assert reason == "VALID"
