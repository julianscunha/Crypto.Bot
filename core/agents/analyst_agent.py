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

    async def on_message(self, message):

        if not isinstance(message, MarketDataMessage):
            return

        payload = message.payload

        analysis = "BULLISH"

        if payload.close < payload.open:
            analysis = "BEARISH"

        analysis_payload = MarketAnalysisPayload(
            user_id=payload.user_id,
            symbol=payload.symbol,
            analysis=analysis,
            reference_price=payload.close,
            confidence=0.85
        )

        analysis_message = MarketAnalysisMessage(
            sender="AnalystAgent",
            payload=analysis_payload
        )

        await self.bus.publish(
            analysis_message
        )