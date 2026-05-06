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

        self.price_history = {}

    def on_message(self, message):

        if not isinstance(message, MarketDataMessage):
            return

        user_id = message.user_id

        symbol = message.payload.symbol
        price = message.payload.price

        key = f"{user_id}:{symbol}"

        if key not in self.price_history:
            self.price_history[key] = []

        history = self.price_history[key]

        history.append(price)

        history[:] = history[-20:]

        if len(history) < 5:
            return

        trend = "SIDEWAYS"

        if history[-1] > history[0]:
            trend = "UP"

        elif history[-1] < history[0]:
            trend = "DOWN"

        confidence = abs(
            history[-1] - history[0]
        )

        self.bus.publish(
            MarketAnalysisMessage(
                user_id=user_id,
                payload=MarketAnalysisPayload(
                    symbol=symbol,
                    trend=trend,
                    confidence=round(confidence, 2),
                    price=price
                )
            )
        )