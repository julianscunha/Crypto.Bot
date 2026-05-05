from core.agents.base_agent import BaseAgent
from core.contracts.messages import TradeProposalMessage, RiskDecisionMessage


class RiskAgent(BaseAgent):

    def on_message(self, message):

        if isinstance(message, TradeProposalMessage):

            approved = message.payload.confidence > 0.6

            decision = RiskDecisionMessage(
                sender=self.name,
                user_id=message.user_id,
                payload={
                    "approved": approved
                },
                explanation="Basic risk check"
            )

            self.publish(decision)