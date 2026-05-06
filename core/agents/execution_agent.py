# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent

from core.contracts.messages import (
    RiskDecisionMessage
)

from data.storage.positions_repository import (
    open_position,
    get_open_position,
    update_position,
    close_position
)

from data.storage.metrics import calculate_metrics


class ExecutionAgent(BaseAgent):

    def on_message(self, message):

        if not isinstance(message, RiskDecisionMessage):
            return

        payload = message.payload

        user_id = message.user_id

        symbol = payload.symbol

        action = payload.action
        approved = payload.approved

        price = payload.price
        quantity = payload.quantity

        if not approved and action != "HOLD":
            return

        position = get_open_position(
            user_id,
            symbol
        )

        # =================================================
        # OPEN
        # =================================================

        if action == "OPEN" and position is None:

            open_position(
                user_id=user_id,

                symbol=symbol,

                action="BUY",

                entry_price=price,

                quantity=quantity,

                stop_loss=payload.stop_loss,

                take_profit=payload.take_profit,

                trailing_stop=payload.trailing_stop,

                breakeven_enabled=False
            )

            print(
                f"[EXECUTION] "
                f"{symbol} "
                f"OPEN BUY @ {round(price,2)} "
                f"| SL={payload.stop_loss} "
                f"| TP={payload.take_profit}"
            )

        # =================================================
        # HOLD
        # =================================================

        elif action == "HOLD" and position is not None:

            update_position(
                position_id=position["id"],

                current_price=price,

                stop_loss=payload.stop_loss,

                trailing_stop=payload.trailing_stop,

                breakeven_enabled=payload.breakeven_enabled
            )

        # =================================================
        # CLOSE
        # =================================================

        elif action == "CLOSE" and position is not None:

            pnl = round(
                (
                    price
                    - position["entry_price"]
                ) * position["quantity"],
                2
            )

            close_position(
                position["id"],
                pnl
            )

            metrics = calculate_metrics(user_id)

            print(
                f"[EXECUTION] "
                f"{symbol} "
                f"CLOSE @ {round(price,2)} "
                f"| PnL={round(pnl,2)} "
                f"| Equity={metrics['equity']} "
                f"| DD={metrics['max_drawdown']} "
                f"| PF={metrics['profit_factor']} "
                f"| WR={metrics['winrate']}"
            )