class TradeOrchestrator:
    def __init__(self):
        self.trades = {}

    def create_trade(self, trade_id):
        self.trades[trade_id] = {"state": "IDLE"}
