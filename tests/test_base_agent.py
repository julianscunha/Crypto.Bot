# -*- coding: utf-8 -*-

"""
Unit tests for core/agents/base_agent.py

BaseAgent is unused scaffolding (no agent in core/agents/* inherits
from it), but it's still real code that should not silently break.

Regression covered: publish() previously called
self.bus.publish(message) without awaiting it, even though
EventBus.publish() is a coroutine. That created an un-awaited
coroutine object and never delivered the message.
"""

import pytest

from core.agents.base_agent import BaseAgent

from core.bus.event_bus import EventBus


class _ConcreteAgent(BaseAgent):

    def __init__(self, bus):

        super().__init__(
            name="ConcreteAgent",
            bus=bus
        )

        self.received = []

    def on_message(self, message):

        self.received.append(message)


class TestBaseAgentInit:

    def test_subscribes_to_bus_on_init(self):

        bus = EventBus()

        agent = _ConcreteAgent(bus)

        assert agent in bus.subscribers

    def test_stores_name(self):

        bus = EventBus()

        agent = _ConcreteAgent(bus)

        assert agent.name == "ConcreteAgent"


class TestBaseAgentPublish:

    @pytest.mark.asyncio
    async def test_publish_actually_delivers_message(self):

        bus = EventBus()

        sender = _ConcreteAgent(bus)

        receiver = _ConcreteAgent(bus)

        await sender.publish("hello")

        # both sender and receiver are subscribed (fan-out bus), so
        # the message must have actually reached on_message -- if
        # publish() weren't awaited, this would silently never fire
        assert "hello" in receiver.received

        assert "hello" in sender.received


class TestOnMessageNotImplemented:

    def test_raises_not_implemented_by_default(self):

        bus = EventBus()

        class _BareAgent(BaseAgent):

            def __init__(self, bus):

                super().__init__(
                    name="Bare",
                    bus=bus
                )

        agent = _BareAgent(bus)

        with pytest.raises(NotImplementedError):

            agent.on_message("anything")
