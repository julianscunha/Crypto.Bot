from core.agents.base_agent import BaseAgent
from core.contracts.messages import MarketAnalysisMessage, TradeProposalMessage


class StrategyAgent(BaseAgent):

    def on_message(self, message):

        if isinstance(message, MarketAnalysisMessage):

            if message.payload.trend == "bullish":

                trade = TradeProposalMessage(
                    sender=self.name,
                    user_id=message.user_id,
                    payload={
                        "action": "BUY",
                        "confidence": message.payload.confidence
                    },
                    explanation="Trend bullish"
                )

                self.publish(trade)