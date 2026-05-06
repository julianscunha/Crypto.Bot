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

    def on_message(self, message):

        if not isinstance(message, MarketAnalysisMessage):
            return

        payload = message.payload

        signal = "BUY"

        if payload.analysis == "BEARISH":
            signal = "SELL"

        result = StrategySignalPayload(
            user_id=payload.user_id,
            symbol=payload.symbol,
            signal=signal,
            price=payload.price
        )

        self.bus.publish(
            StrategySignalMessage(
                sender="StrategyAgent",
                payload=result
            )
        )