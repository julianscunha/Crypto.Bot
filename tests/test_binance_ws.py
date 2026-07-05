# -*- coding: utf-8 -*-

"""
Tests for data/ingestion/binance_ws.py

BinanceWS.start() opens a real websocket connection in an infinite
loop, so it's tested here using a mocked websocket connection rather
than a live one. This also serves as a regression test for the
market_state.register_kline() bug: a kline message reaching this code
path previously raised AttributeError on every closed candle.
"""

import json

import asyncio

import pytest

from unittest.mock import AsyncMock, MagicMock, patch

from data.ingestion.binance_ws import BinanceWS

from core.bus.event_bus import EventBus

from core.state.market_state import market_state


def _kline_message(symbol="BTCUSDT", closed=True, close_price="105.5"):

    return json.dumps({
        "k": {
            "s": symbol,
            "x": closed,
            "o": "100.0",
            "h": "106.0",
            "l": "99.0",
            "c": close_price,
            "v": "12.5"
        }
    })


class TestBuildStreamUrl:

    def test_builds_url_with_lowercase_symbols_and_interval(self):

        bus = EventBus()

        ws = BinanceWS(bus=bus, user_id=0)

        url = ws.build_stream_url()

        assert url.startswith(
            "wss://stream.binance.com:9443/ws/"
        )

        for symbol in ws.symbols:

            assert symbol in url

            assert f"{symbol}@kline_{ws.interval}" in url


class TestPrintSymbolDivider:

    def test_does_not_raise(self, capsys):

        bus = EventBus()

        ws = BinanceWS(bus=bus, user_id=0)

        ws.print_symbol_divider("BTCUSDT")

        captured = capsys.readouterr()

        assert "BTCUSDT" in captured.out


class _FakeWebSocket:

    """
    Minimal async context manager + async iterator-ish mock that
    yields a fixed sequence of raw messages from recv(), then raises
    asyncio.CancelledError to break the outer `while True` loop
    cleanly once the test has seen what it needs to see.
    """

    def __init__(self, messages):

        self._messages = list(messages)

    async def __aenter__(self):

        return self

    async def __aexit__(self, exc_type, exc, tb):

        return False

    async def recv(self):

        if not self._messages:

            raise asyncio.CancelledError()

        return self._messages.pop(0)


class TestStartProcessesKlineMessages:

    @pytest.mark.asyncio
    async def test_closed_kline_publishes_market_data_message(self):

        bus = EventBus()

        received = []

        class _Spy:

            async def on_message(self, message):

                received.append(message)

        bus.subscribe(_Spy())

        ws = BinanceWS(bus=bus, user_id=0)

        fake_socket = _FakeWebSocket([
            _kline_message(closed=True)
        ])

        with patch(
            "data.ingestion.binance_ws.websockets.connect",
            return_value=fake_socket
        ):

            with pytest.raises(asyncio.CancelledError):

                await ws.start()

        assert len(received) == 1

        assert received[0].payload.symbol == "BTCUSDT"

        assert received[0].payload.close == 105.5

    @pytest.mark.asyncio
    async def test_open_kline_is_skipped_not_published(self):

        bus = EventBus()

        received = []

        class _Spy:

            async def on_message(self, message):

                received.append(message)

        bus.subscribe(_Spy())

        ws = BinanceWS(bus=bus, user_id=0)

        fake_socket = _FakeWebSocket([
            # not yet closed -> must be skipped
            _kline_message(closed=False),
        ])

        with patch(
            "data.ingestion.binance_ws.websockets.connect",
            return_value=fake_socket
        ):

            with pytest.raises(asyncio.CancelledError):

                await ws.start()

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_kline_message_updates_market_state_without_raising(
        self
    ):

        # regression test: this previously raised AttributeError via
        # market_state.register_kline() not existing

        market_state.reset()

        bus = EventBus()

        ws = BinanceWS(bus=bus, user_id=0)

        fake_socket = _FakeWebSocket([
            _kline_message(closed=True)
        ])

        with patch(
            "data.ingestion.binance_ws.websockets.connect",
            return_value=fake_socket
        ):

            with pytest.raises(asyncio.CancelledError):

                await ws.start()

        assert market_state.total_market_messages >= 1

        assert "BTCUSDT" in market_state.active_symbols

    @pytest.mark.asyncio
    async def test_non_kline_message_is_ignored(self):

        bus = EventBus()

        received = []

        class _Spy:

            async def on_message(self, message):

                received.append(message)

        bus.subscribe(_Spy())

        ws = BinanceWS(bus=bus, user_id=0)

        fake_socket = _FakeWebSocket([
            json.dumps({"not_a_kline": True})
        ])

        with patch(
            "data.ingestion.binance_ws.websockets.connect",
            return_value=fake_socket
        ):

            with pytest.raises(asyncio.CancelledError):

                await ws.start()

        assert len(received) == 0
