# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent

from core.contracts.messages import (
    RiskDecisionMessage
)

from data.storage.positions_repository import (
    open_position,
    get_open_position,
    close_position
)

from data.storage.metrics import calculate_metrics


class ExecutionAgent(BaseAgent):

    def on_message(self, message):

        if not isinstance(message, RiskDecisionMessage):
            return

        payload = message.payload

        user_id = message.user_id

        action = payload.action
        approved = payload.approved

        price = payload.price
        quantity = payload.quantity

        if not approved:
            return

        position = get_open_position(user_id)

        # ==================================================
        # OPEN
        # ==================================================

        if action == "OPEN" and position is None:

            open_position(
                user_id=user_id,
                action="BUY",
                price=price,
                quantity=quantity
            )

            print(
                f"[EXECUTION] OPEN BUY @ {round(price,2)} "
                f"| qty={round(quantity,2)}"
            )

        # ==================================================
        # CLOSE
        # ==================================================

        elif action == "CLOSE" and position is not None:

            entry_price = position["price"]

            pnl = (
                (price - entry_price)
                * position["quantity"]
            )

            close_position(
                position["id"],
                pnl
            )

            metrics = calculate_metrics(user_id)

            print(
                f"[EXECUTION] CLOSE @ {round(price,2)} "
                f"| PnL={round(pnl,2)} "
                f"| {metrics}"
            )