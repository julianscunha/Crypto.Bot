# -*- coding: utf-8 -*-

import json
import asyncio
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

        self.interval = "1m"

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
    # START
    # =====================================================

    async def start(self):

        stream_url = (
            self.build_stream_url()
        )

        while True:

            try:

                async with websockets.connect(
                    stream_url
                ) as websocket:

                    market_state.set_websocket_connected(
                        True
                    )

                    log(
                        "SYSTEM",
                        "BINANCE WEBSOCKET CONNECTED",
                    )

                    while True:

                        raw_data = (
                            await websocket.recv()
                        )

                        data = json.loads(
                            raw_data
                        )

                        if "k" not in data:
                            continue

                        kline = data["k"]

                        # =================================================
                        # ONLY CLOSED CANDLES
                        # =================================================

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

                        # =================================================
                        # SYMBOL SEPARATOR
                        # =================================================

                        print()

                        print(
                            (
                                "=" * 26
                                + f" {symbol} "
                                + "=" * 26
                            )
                        )

                        # =================================================
                        # MARKET LOG
                        # =================================================

                        log(
                            "MARKET",
                            (
                                f"KLINE "
                                f"{symbol} "
                                f"close={payload.close}"
                            )
                        )

                        # =================================================
                        # PUBLISH
                        # =================================================

                        await self.bus.publish(
                            message
                        )

            except Exception as e:

                market_state.set_websocket_connected(
                    False
                )

                log(
                    "SYSTEM",
                    f"BINANCE ERROR {e}",
                    "ERROR"
                )

                await asyncio.sleep(5)