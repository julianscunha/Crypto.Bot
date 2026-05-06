# -*- coding: utf-8 -*-

import asyncio
import random

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)


class BinanceWS:

    SYMBOLS = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT"
    ]

    def __init__(self, bus):

        self.bus = bus
        self.running = True

        self.prices = {
            "BTCUSDT": 100.0,
            "ETHUSDT": 80.0,
            "SOLUSDT": 50.0,
            "BNBUSDT": 70.0
        }

    async def start(self):

        while self.running:

            for symbol in self.SYMBOLS:

                self.prices[symbol] += random.uniform(-2, 2)

                price = round(self.prices[symbol], 2)

                self.bus.publish(
                    MarketDataMessage(
                        user_id=1,
                        payload=MarketDataPayload(
                            symbol=symbol,
                            price=price
                        )
                    )
                )

            await asyncio.sleep(2)

    def stop(self):
        self.running = False