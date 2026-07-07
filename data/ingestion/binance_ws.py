# -*- coding: utf-8 -*-

import json
import asyncio
import random
import time

import websockets

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)

from core.utils.console_logger import (
    log
)

from core.config.settings import (
    settings
)

from core.state.market_state import (
    market_state
)

BINANCE_WS_URL = (
    "wss://stream.binance.com:9443/ws"
)


class BinanceWS:

    def __init__(
        self,
        bus,
        user_id: int
    ):

        self.bus = bus

        self.user_id = user_id

        self.symbols = [
            symbol.lower()
            for symbol in settings.SYMBOLS
        ]

        self.interval = (
            settings.KLINE_INTERVAL
        )

        # =====================================================
        # RESILIENCE
        # =====================================================

        self.reconnect_attempts = 0

        self.last_message_at = (
            time.time()
        )

    # =====================================================
    # STREAMS
    # =====================================================

    def build_stream_url(self):

        streams = []

        for symbol in self.symbols:

            streams.append(
                f"{symbol}@kline_{self.interval}"
            )

        return (
            BINANCE_WS_URL
            + "/"
            + "/".join(streams)
        )

    # =====================================================
    # SYMBOL DIVIDER
    # =====================================================

    def print_symbol_divider(
        self,
        symbol: str
    ):

        title = f" {symbol} "

        total_width = 60

        side = (
            total_width - len(title)
        ) // 2

        print()

        print(
            (
                "=" * side
                + title
                + "=" * side
            )
        )

    # =====================================================
    # START
    # =====================================================

    async def start(self):

        stream_url = (
            self.build_stream_url()
        )

        while True:

            try:

                log(
                    "WEBSOCKET",
                    "CONNECTING",
                    "INFO"
                )

                async with websockets.connect(
                    stream_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10
                ) as websocket:

                    # =========================================
                    # RESET RECONNECT COUNTER
                    # =========================================

                    self.reconnect_attempts = 0

                    market_state.set_websocket_connected(
                        True
                    )

                    log(
                        "SYSTEM",
                        "WEBSOCKET CONNECTED",
                        "SUCCESS"
                    )

                    while True:

                        # =====================================
                        # STALE STREAM PROTECTION
                        # =====================================

                        raw_data = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=90
                        )

                        self.last_message_at = (
                            time.time()
                        )

                        data = json.loads(
                            raw_data
                        )

                        if "k" not in data:

                            continue

                        kline = data["k"]

                        # =====================================
                        # ONLY CLOSED CANDLES
                        # =====================================

                        if not kline["x"]:

                            continue

                        symbol = kline["s"]

                        market_state.register_kline(
                            symbol
                        )

                        payload = (
                            MarketDataPayload(
                                user_id=self.user_id,
                                symbol=symbol,
                                open=float(kline["o"]),
                                high=float(kline["h"]),
                                low=float(kline["l"]),
                                close=float(kline["c"]),
                                volume=float(kline["v"])
                            )
                        )

                        message = (
                            MarketDataMessage(
                                sender="BinanceWS",
                                payload=payload
                            )
                        )

                        # =====================================
                        # SYMBOL DIVIDER
                        # =====================================

                        self.print_symbol_divider(
                            symbol
                        )

                        # =====================================
                        # MARKET LOG
                        # =====================================

                        log(
                            "MARKET",
                            (
                                f"KLINE "
                                f"close={payload.close}"
                            )
                        )

                        # =====================================
                        # PUBLISH
                        # =====================================

                        await self.bus.publish(
                            message
                        )

            except asyncio.TimeoutError:

                market_state.set_websocket_connected(
                    False
                )

                log(
                    "WEBSOCKET",
                    "STALE STREAM",
                    "WARNING"
                )

            except Exception as error:

                market_state.set_websocket_connected(
                    False
                )

                self.reconnect_attempts += 1

                delay = min(
                    2 ** self.reconnect_attempts,
                    60
                )

                delay += random.uniform(
                    0,
                    3
                )

                log(
                    "WEBSOCKET",
                    (
                        f"RECONNECT "
                        f"attempt={self.reconnect_attempts} "
                        f"reason={type(error).__name__}: {error}"
                    ),
                    "WARNING"
                )

                await asyncio.sleep(
                    delay
                )
