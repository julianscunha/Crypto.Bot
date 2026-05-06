# -*- coding: utf-8 -*-

from core.contracts.messages import (
    StrategySignalMessage,
    RiskDecisionMessage,
    RiskDecisionPayload
)

from data.storage.positions_repository import (
    PositionsRepository
)

from data.storage.metrics import (
    MetricsStorage
)


class RiskAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = PositionsRepository()
        self.metrics = MetricsStorage()

        self.max_portfolio_exposure = 10000

        self.bus.subscribe(self)

    def on_message(self, message):

        if not isinstance(message, StrategySignalMessage):
            return

        payload = message.payload

        existing = self.positions.get_open_position(
            user_id=payload.user_id,
            symbol=payload.symbol
        )

        if existing:
            return

        exposure = self.metrics.total_open_exposure(
            user_id=payload.user_id
        )

        if exposure >= self.max_portfolio_exposure:
            return

        result = RiskDecisionPayload(
            user_id=payload.user_id,
            symbol=payload.symbol,
            signal=payload.signal,
            price=payload.price,
            quantity=2.0,
            stop_loss=payload.price * 0.98,
            take_profit=payload.price * 1.04,
            trailing_stop=payload.price * 0.015
        )

        self.bus.publish(
            RiskDecisionMessage(
                sender="RiskAgent",
                payload=result
            )
        )