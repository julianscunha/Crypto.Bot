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
        user_id: int
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

                current_price = round(
                    random.uniform(90, 120),
                    2
                )

                payload = MarketDataPayload(
                    user_id=self.user_id,
                    symbol=symbol,
                    open=current_price,
                    close=current_price,
                    high=round(current_price * 1.01, 2),
                    low=round(current_price * 0.99, 2),
                    volume=round(
                        random.uniform(1000, 5000),
                        2
                    )
                )

                message = MarketDataMessage(
                    sender="BinanceWS",
                    payload=payload
                )

                await self.bus.publish(
                    message
                )

            await asyncio.sleep(2)