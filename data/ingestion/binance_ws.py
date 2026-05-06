# -*- coding: utf-8 -*-

import asyncio
import random

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)


class BinanceWS:

    def __init__(self, bus):
        self.bus = bus
        self.running = True

    async def start(self):

        price = 100.0

        while self.running:

            price += random.uniform(-2, 2)

            msg = MarketDataMessage(
                user_id=1,
                payload=MarketDataPayload(
                    symbol="BTCUSDT",
                    price=round(price, 2)
                )
            )

            self.bus.publish(msg)

            await asyncio.sleep(2)

    def stop(self):
        self.running = False