# -*- coding: utf-8 -*-

"""
Unit test for core/agents/analyst_agent.py's on_message, isolated
from the rest of the pipeline: only AnalystAgent is subscribed to
the bus, plus a plain capturing subscriber that records whatever it
forwards downstream.

Exercises the main relay path: a MarketDataMessage comes in and a
MarketAnalysisMessage comes out, carrying the same user_id/symbol
and a reference_price taken from the candle's close.
"""

import pytest

from core.agents.analyst_agent import AnalystAgent

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload,
    MarketAnalysisMessage
)

from core.bus.event_bus import EventBus


class _Capture:

    def __init__(self):
        self.messages = []

    async def on_message(self, message):
        self.messages.append(message)


class TestAnalystAgentOnMessage:

    @pytest.mark.asyncio
    async def test_forwards_a_market_analysis_message_for_a_candle(
        self
    ):

        bus = EventBus()

        AnalystAgent(bus)

        capture = _Capture()

        bus.subscribe(capture)

        payload = MarketDataPayload(
            user_id=800,
            symbol="BTCUSDT",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=payload
            )
        )

        # capture is subscribed to the same bus as everyone else, so
        # it also receives the original MarketDataMessage the test
        # published -- only look at what AnalystAgent itself forwarded.
        forwarded_messages = [
            message
            for message in capture.messages
            if isinstance(message, MarketAnalysisMessage)
        ]

        assert len(forwarded_messages) == 1

        forwarded = forwarded_messages[0]

        assert forwarded.payload.user_id == 800

        assert forwarded.payload.symbol == "BTCUSDT"

        assert forwarded.payload.reference_price == 100.5

        # A single candle is nowhere near minimum_structure_candles,
        # so the structure engine reports invalid -> NEUTRAL.
        assert forwarded.payload.analysis == "NEUTRAL"
