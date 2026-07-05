# -*- coding: utf-8 -*-

"""
Unit tests for core/bus/event_bus.py
"""

import pytest

from core.bus.event_bus import (
    EventBus
)


class _RecordingSubscriber:

    def __init__(self):

        self.received = []

    async def on_message(self, message):

        self.received.append(message)


class _SyncSubscriber:

    def __init__(self):

        self.received = []

    def on_message(self, message):

        self.received.append(message)


class _FailingSubscriber:

    def on_message(self, message):

        raise ValueError("boom")


class _NoOnMessage:

    pass


class TestSubscribe:

    def test_subscribe_adds_subscriber(self):

        bus = EventBus()

        sub = _RecordingSubscriber()

        bus.subscribe(sub)

        assert sub in bus.subscribers

    def test_subscribe_is_idempotent(self):

        bus = EventBus()

        sub = _RecordingSubscriber()

        bus.subscribe(sub)

        bus.subscribe(sub)

        assert bus.subscribers.count(sub) == 1

    def test_subscribe_rejects_object_without_on_message(self):

        bus = EventBus()

        invalid = _NoOnMessage()

        bus.subscribe(invalid)

        assert invalid not in bus.subscribers


class TestUnsubscribe:

    def test_unsubscribe_removes_subscriber(self):

        bus = EventBus()

        sub = _RecordingSubscriber()

        bus.subscribe(sub)

        bus.unsubscribe(sub)

        assert sub not in bus.subscribers

    def test_unsubscribe_unknown_subscriber_does_not_raise(self):

        bus = EventBus()

        sub = _RecordingSubscriber()

        bus.unsubscribe(sub)


class TestPublish:

    @pytest.mark.asyncio
    async def test_publish_delivers_to_async_subscriber(self):

        bus = EventBus()

        sub = _RecordingSubscriber()

        bus.subscribe(sub)

        await bus.publish("hello")

        assert sub.received == ["hello"]

    @pytest.mark.asyncio
    async def test_publish_delivers_to_sync_subscriber(self):

        bus = EventBus()

        sub = _SyncSubscriber()

        bus.subscribe(sub)

        await bus.publish("hello")

        assert sub.received == ["hello"]

    @pytest.mark.asyncio
    async def test_publish_fans_out_to_all_subscribers(self):

        bus = EventBus()

        sub_a = _RecordingSubscriber()

        sub_b = _RecordingSubscriber()

        bus.subscribe(sub_a)

        bus.subscribe(sub_b)

        await bus.publish("event")

        assert sub_a.received == ["event"]

        assert sub_b.received == ["event"]

    @pytest.mark.asyncio
    async def test_publish_isolates_subscriber_failure(self):

        bus = EventBus()

        failing = _FailingSubscriber()

        healthy = _RecordingSubscriber()

        bus.subscribe(failing)

        bus.subscribe(healthy)

        # must not raise, despite the failing subscriber
        await bus.publish("event")

        assert healthy.received == ["event"]

    @pytest.mark.asyncio
    async def test_publish_increments_telemetry(self):

        bus = EventBus()

        sub = _RecordingSubscriber()

        bus.subscribe(sub)

        await bus.publish("event")

        telemetry = bus.get_telemetry()

        assert telemetry["total_published_messages"] == 1

        assert telemetry["total_successful_deliveries"] == 1

        assert telemetry["total_failed_deliveries"] == 0

    @pytest.mark.asyncio
    async def test_publish_tracks_failed_deliveries(self):

        bus = EventBus()

        failing = _FailingSubscriber()

        bus.subscribe(failing)

        await bus.publish("event")

        telemetry = bus.get_telemetry()

        assert telemetry["total_failed_deliveries"] == 1

        assert (
            telemetry["delivery_failures"]["_FailingSubscriber"]
            == 1
        )


class TestTelemetry:

    def test_reset_telemetry_clears_counters(self):

        bus = EventBus()

        bus.total_published_messages = 5

        bus.total_successful_deliveries = 4

        bus.total_failed_deliveries = 1

        bus.delivery_failures["X"] = 1

        bus.reset_telemetry()

        assert bus.total_published_messages == 0

        assert bus.total_successful_deliveries == 0

        assert bus.total_failed_deliveries == 0

        assert dict(bus.delivery_failures) == {}
