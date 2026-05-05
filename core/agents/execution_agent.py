from core.agents.base_agent import BaseAgent
from core.contracts.messages import RiskDecisionMessage


class ExecutionAgent(BaseAgent):

    def on_message(self, message):

        if isinstance(message, RiskDecisionMessage):

            if message.payload.approved:
                print(f"[EXECUTION] Trade executed (paper)")
            else:
                print(f"[EXECUTION] Trade rejected")