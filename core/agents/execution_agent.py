# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent
from core.contracts.messages import RiskDecisionMessage, MarketDataMessage

from data.storage.positions_repository import (
    open_position,
    get_open_position,
    close_position
)

from data.storage.metrics import calculate_metrics


class ExecutionAgent(BaseAgent):

    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.last_price = {}

    def on_message(self, message):

        # Atualiza preço atual
        if isinstance(message, MarketDataMessage):
            self.last_price[message.user_id] = message.payload.price

        if isinstance(message, RiskDecisionMessage):

            user_id = message.user_id
            price = self.last_price.get(user_id)

            if price is None:
                return

            position = get_open_position(user_id)

            # === ABRIR POSIÇÃO ===
            if message.payload.approved and position is None:

                open_position(
                    user_id=user_id,
                    action="BUY",
                    price=price,
                    quantity=1
                )

                print(f"[EXECUTION] OPEN BUY @ {price}")

            # === FECHAR POSIÇÃO ===
            elif position is not None:

                entry_price = position["price"]
                quantity = position["quantity"]

                pnl = (price - entry_price) * quantity

                close_position(position["id"], pnl)

                metrics = calculate_metrics(user_id)

                print(f"[EXECUTION] CLOSE @ {price} | PnL: {round(pnl,2)} | Metrics: {metrics}")