# -*- coding: utf-8 -*-

from core.contracts.messages import (
    RiskDecisionMessage
)

from data.storage.positions_repository import (
    PositionsRepository
)

from data.storage.metrics import (
    MetricsStorage
)


class ExecutionAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = PositionsRepository()
        self.metrics = MetricsStorage()

        self.bus.subscribe(self)

    def on_message(self, message):

        if not isinstance(message, RiskDecisionMessage):
            return

        payload = message.payload

        if payload.signal != "BUY":
            return

        trade = self.positions.create_position(
            user_id=payload.user_id,
            symbol=payload.symbol,
            action=payload.signal,
            entry_price=payload.price,
            quantity=payload.quantity,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            trailing_stop=payload.trailing_stop,

            breakeven_enabled=True
        )

        print(
            f"[EXECUTION] OPEN BUY "
            f"{payload.symbol} "
            f"@ {payload.price} "
            f"| qty={payload.quantity}"
        )

        exit_price = payload.price * 1.02

        pnl = (
            exit_price - payload.price
        ) * payload.quantity

        self.positions.close_position(
            trade_id=trade.id,
            exit_price=exit_price,
            pnl=pnl
        )

        metrics = self.metrics.get_metrics(
            user_id=payload.user_id
        )

        print(
            f"[EXECUTION] CLOSE "
            f"{payload.symbol} "
            f"@ {round(exit_price, 2)} "
            f"| PnL={round(pnl, 2)} "
            f"| {metrics}"
        )