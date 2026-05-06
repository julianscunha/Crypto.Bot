# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketAnalysisMessage,
    StrategySignalMessage,
    StrategySignalPayload
)


class StrategyAgent:

    def __init__(self, bus):

        self.bus = bus

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(message, MarketAnalysisMessage):
            return

        payload = message.payload

        signal = "HOLD"

        if payload.analysis == "BULLISH":
            signal = "BUY"

        signal_payload = StrategySignalPayload(
            user_id=payload.user_id,
            symbol=payload.symbol,
            signal=signal,
            price=payload.price
        )

        signal_message = StrategySignalMessage(
            sender="StrategyAgent",
            payload=signal_payload
        )

        await self.bus.publish(
            signal_message
        )