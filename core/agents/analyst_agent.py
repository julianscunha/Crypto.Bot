# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent

from core.contracts.messages import (
    MarketDataMessage,
    MarketAnalysisMessage,
    MarketAnalysisPayload
)


class AnalystAgent(BaseAgent):

    def __init__(self, name, bus):
        super().__init__(name, bus)

        self.last_price = {}

    def on_message(self, message):

        if not isinstance(message, MarketDataMessage):
            return

        user_id = message.user_id
        price = message.payload.price

        previous = self.last_price.get(user_id)

        if previous is None:
            self.last_price[user_id] = price
            return

        trend = "SIDEWAYS"
        confidence = 0.5

        if price > previous:
            trend = "BULLISH"
            confidence = 0.8

        elif price < previous:
            trend = "BEARISH"
            confidence = 0.8

        self.last_price[user_id] = price

        analysis = MarketAnalysisMessage(
            user_id=user_id,
            payload=MarketAnalysisPayload(
                trend=trend,
                confidence=confidence,
                price=price
            )
        )

        self.bus.publish(analysis)