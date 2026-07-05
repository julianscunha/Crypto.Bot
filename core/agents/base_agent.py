# NOTE: Early scaffolding base class, not used by any of the agents
# in core/agents/* -- each agent (AnalystAgent, StrategyAgent,
# RiskAgent, ExecutionAgent, PositionManagerAgent) manages its own
# bus.subscribe()/await bus.publish() directly instead of inheriting
# from this class.
#
# publish() is async because EventBus.publish() is a coroutine;
# calling it without awaiting (as an earlier version of this file
# did) would silently create an un-awaited coroutine and never
# actually deliver the message.

class BaseAgent:
    def __init__(self, name, bus):
        self.name = name
        self.bus = bus
        self.bus.subscribe(self)

    async def publish(self, message):
        await self.bus.publish(message)

    def on_message(self, message):
        raise NotImplementedError
