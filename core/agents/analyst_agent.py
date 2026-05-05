from core.agents.base_agent import BaseAgent
from core.contracts.messages import MarketDataMessage, MarketAnalysisMessage


class AnalystAgent(BaseAgent):

    def on_message(self, message):

        if isinstance(message, MarketDataMessage):

            trend = "bullish" if message.payload.price > message.payload.open else "bearish"

            analysis = MarketAnalysisMessage(
                sender=self.name,
                user_id=message.user_id,
                payload={
                    "trend": trend,
                    "volatility": "medium",
                    "confidence": 0.7
                },
                explanation="price vs open"
            )

            self.publish(analysis)