# -*- coding: utf-8 -*-

"""
Unit tests for core/agents/strategy_agent.py's on_message, isolated
from the rest of the pipeline. StrategyAgent's own services
(market_structure_service, signal_quality_service) and the module
level `atr` helper are stubbed out via monkeypatch so each test
controls the structure/ATR/quality outcome directly, instead of
having to feed dozens of real candles to produce a valid structure.

Exercises the main relay path: a MarketAnalysisMessage with enough
confidence and a valid structure produces a BUY StrategySignalMessage
carrying entry_price/atr/user_id/symbol through; and the LOW_SIGNAL_
STRENGTH branch that blocks before a signal is ever built.
"""

import pytest

from core.agents.strategy_agent import StrategyAgent

import core.agents.strategy_agent as strategy_agent_module

from core.contracts.messages import (
    MarketAnalysisMessage,
    MarketAnalysisPayload,
    StrategySignalMessage
)

from core.bus.event_bus import EventBus

from core.state.market_state import market_state


class _Capture:

    def __init__(self):
        self.messages = []

    async def on_message(self, message):
        self.messages.append(message)


def _make_analysis_payload(
    user_id=900,
    symbol="BTCUSDT",
    reference_price=100.0,
    confidence=0.9
):

    return MarketAnalysisPayload(
        user_id=user_id,
        symbol=symbol,
        analysis="BULLISH",
        reference_price=reference_price,
        confidence=confidence
    )


@pytest.fixture(autouse=True)
def _reset_market_state():

    market_state.reset()

    yield

    market_state.reset()


class TestStrategyAgentOnMessage:

    @pytest.mark.asyncio
    async def test_forwards_a_buy_signal_when_structure_and_confidence_pass(
        self,
        monkeypatch
    ):

        bus = EventBus()

        agent = StrategyAgent(bus)

        capture = _Capture()

        bus.subscribe(capture)

        monkeypatch.setattr(
            agent.market_structure,
            "get_prices",
            lambda user_id, symbol: [100.0] * 30
        )

        monkeypatch.setattr(
            agent.market_structure,
            "analyze_structure",
            lambda user_id, symbol: {"valid": True, "reason": "BULLISH_STRUCTURE"}
        )

        monkeypatch.setattr(
            strategy_agent_module,
            "atr",
            lambda prices: 2.0
        )

        monkeypatch.setattr(
            agent.signal_quality,
            "validate",
            lambda payload: (True, "VALID")
        )

        await bus.publish(
            MarketAnalysisMessage(
                sender="test",
                payload=_make_analysis_payload()
            )
        )

        # capture also receives the original MarketAnalysisMessage the
        # test published -- only look at what StrategyAgent forwarded.
        forwarded_messages = [
            message
            for message in capture.messages
            if isinstance(message, StrategySignalMessage)
        ]

        assert len(forwarded_messages) == 1

        forwarded = forwarded_messages[0]

        assert forwarded.payload.signal == "BUY"

        assert forwarded.payload.user_id == 900

        assert forwarded.payload.symbol == "BTCUSDT"

        assert forwarded.payload.entry_price == 100.0

        assert forwarded.payload.atr == 2.0

    @pytest.mark.asyncio
    async def test_blocks_before_building_a_signal_when_confidence_too_low(
        self,
        monkeypatch
    ):

        bus = EventBus()

        agent = StrategyAgent(bus)

        capture = _Capture()

        bus.subscribe(capture)

        monkeypatch.setattr(
            agent.market_structure,
            "get_prices",
            lambda user_id, symbol: [100.0] * 30
        )

        monkeypatch.setattr(
            agent.market_structure,
            "analyze_structure",
            lambda user_id, symbol: {"valid": True, "reason": "BULLISH_STRUCTURE"}
        )

        monkeypatch.setattr(
            strategy_agent_module,
            "atr",
            lambda prices: 2.0
        )

        await bus.publish(
            MarketAnalysisMessage(
                sender="test",
                payload=_make_analysis_payload(
                    user_id=901,
                    confidence=0.1
                )
            )
        )

        forwarded_signals = [
            message
            for message in capture.messages
            if isinstance(message, StrategySignalMessage)
        ]

        assert forwarded_signals == []

        reasons = market_state.get_blocked_signal_reasons()

        assert reasons.get("LOW_SIGNAL_STRENGTH") == 1
