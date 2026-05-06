# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketDataMessage,
    MarketAnalysisMessage,
    MarketAnalysisPayload
)


class AnalystAgent:

    def __init__(self, bus):

        self.bus = bus

        self.bus.subscribe(self)

    def on_message(self, message):

        if not isinstance(message, MarketDataMessage):
            return

        payload = message.payload

        analysis = "BULLISH"

        if payload.close < payload.open:
            analysis = "BEARISH"

        result = MarketAnalysisPayload(
            user_id=payload.user_id,
            symbol=payload.symbol,
            analysis=analysis,
            price=payload.close
        )

        self.bus.publish(
            MarketAnalysisMessage(
                sender="AnalystAgent",
                payload=result
            )
        )