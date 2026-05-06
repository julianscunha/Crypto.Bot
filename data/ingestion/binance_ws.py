# -*- coding: utf-8 -*-

import asyncio
import random

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)


class BinanceWS:

    def __init__(
        self,
        bus,
        user_id
    ):

        self.bus = bus
        self.user_id = user_id

        self.symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT"
        ]

    async def start(self):

        while True:

            for symbol in self.symbols:

                open_price = round(
                    random.uniform(90, 110),
                    2
                )

                close_price = round(
                    open_price + random.uniform(-5, 5),
                    2
                )

                high_price = round(
                    max(open_price, close_price) + random.uniform(0, 2),
                    2
                )

                low_price = round(
                    min(open_price, close_price) - random.uniform(0, 2),
                    2
                )

                payload = MarketDataPayload(
                    user_id=self.user_id,
                    symbol=symbol,
                    open=open_price,
                    close=close_price,
                    high=high_price,
                    low=low_price,
                    volume=random.uniform(100, 1000)
                )

                self.bus.publish(
                    MarketDataMessage(
                        sender="BinanceWS",
                        payload=payload
                    )
                )

            await asyncio.sleep(2)