import asyncio
import json
import websockets
from datetime import datetime

from core.contracts.messages import MarketDataMessage
from core.workroom.bus import WorkRoomBus


BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"


class BinanceWS:

    def __init__(self, bus: WorkRoomBus, user_id: int = 0):
        self.bus = bus
        self.user_id = user_id

    async def start(self):
        async with websockets.connect(BINANCE_WS_URL) as ws:
            while True:
                raw = await ws.recv()
                data = json.loads(raw)

                k = data.get("k", {})

                msg = MarketDataMessage(
                    sender="binance",
                    user_id=self.user_id,
                    payload={
                        "symbol": k.get("s"),
                        "price": float(k.get("c", 0)),
                        "open": float(k.get("o", 0)),
                        "high": float(k.get("h", 0)),
                        "low": float(k.get("l", 0)),
                        "volume": float(k.get("v", 0)),
                        "closed": k.get("x"),
                    },
                    explanation="Binance real-time kline"
                )

                self.bus.publish(msg)