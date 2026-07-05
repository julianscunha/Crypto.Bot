# NOTE: Early scaffolding stub, superseded by the EventBus-based
# multi-agent pipeline (core/bus/event_bus.py + core/agents/*).
# Not imported or used anywhere in the running system.

class TradeOrchestrator:
    def __init__(self):
        self.trades = {}

    def create_trade(self, trade_id):
        self.trades[trade_id] = {"state": "IDLE"}
