# -*- coding: utf-8 -*-

import asyncio
import random

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)


class BinanceWS:

    def __init__(self, bus, user_id):

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
                    random.uniform(90, 120),
                    2
                )

                close_price = round(
                    open_price * random.uniform(0.98, 1.02),
                    2
                )

                high_price = max(
                    open_price,
                    close_price
                ) * random.uniform(1.0, 1.01)

                low_price = min(
                    open_price,
                    close_price
                ) * random.uniform(0.99, 1.0)

                volume = round(
                    random.uniform(100, 1000),
                    2
                )

                payload = MarketDataPayload(
                    user_id=self.user_id,
                    symbol=symbol,
                    open=open_price,
                    close=close_price,
                    high=round(high_price, 2),
                    low=round(low_price, 2),
                    volume=volume
                )

                message = MarketDataMessage(
                    sender="BinanceWS",
                    payload=payload
                )

                await self.bus.publish(
                    message
                )

            await asyncio.sleep(2)