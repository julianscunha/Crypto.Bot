# -*- coding: utf-8 -*-

import json
import asyncio
import websockets

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)

from colorama import (
    Fore,
    Style,
    init
)

from core.utils.console_logger import (
    log
)

init(autoreset=True)


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
            "btcusdt",
            "ethusdt",
            "solusdt"
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
       
        log(
            "BINANCE",
            f"Connected {stream_url}",
            Fore.LIGHTCYAN_EX
        )
        
        print()

        while True:

            try:

                async with websockets.connect(
                    stream_url
                ) as websocket:

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

                        # ONLY CLOSED CANDLES
                        if not kline["x"]:
                            continue

                        symbol = kline["s"]

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
                       
                        log(
                            "KLINE",
                            f"{symbol} close={payload.close}",
                            Fore.LIGHTWHITE_EX
                        )
                        

                        await self.bus.publish(
                            message
                        )

            except Exception as e: 
                
                log(
                    "BINANCE ERROR",
                    f"{e}",
                    Fore.RED
                )

                await asyncio.sleep(5)