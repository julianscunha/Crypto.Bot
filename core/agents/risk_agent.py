# -*- coding: utf-8 -*-

from core.contracts.messages import (
    StrategySignalMessage,
    RiskDecisionMessage,
    RiskDecisionPayload
)

from data.storage.positions_repository import (
    PositionsRepository
)


class RiskAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = PositionsRepository()

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(message, StrategySignalMessage):
            return

        payload = message.payload

        if payload.signal != "BUY":
            return

        existing_position = (
            self.positions.get_open_position(
                user_id=payload.user_id,
                symbol=payload.symbol
            )
        )

        if existing_position:
            return

        entry_price = payload.price

        stop_loss = round(
            entry_price * 0.98,
            2
        )

        take_profit = round(
            entry_price * 1.02,
            2
        )

        trailing_stop = round(
            entry_price * 0.015,
            4
        )

        quantity = 2.0

        decision_payload = RiskDecisionPayload(
            user_id=payload.user_id,
            symbol=payload.symbol,
            signal=payload.signal,
            price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop
        )

        decision_message = RiskDecisionMessage(
            sender="RiskAgent",
            payload=decision_payload
        )

        await self.bus.publish(
            decision_message
        )