# -*- coding: utf-8 -*-

from core.contracts.messages import (
    RiskDecisionMessage
)

from data.storage.repositories.trades_repository import (
    TradesRepository
)

from data.storage.metrics import (
    MetricsStorage
)


from colorama import Fore, Style, init

init(autoreset=True)

class ExecutionAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = TradesRepository()

        self.metrics = MetricsStorage()

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            RiskDecisionMessage
        ):
            return

        payload = message.payload

        if payload.signal != "BUY":
            return

        if self.positions.has_open_trade(
            payload.user_id,
            payload.symbol
        ):
            return

        self.positions.create_trade(
            user_id=payload.user_id,
            symbol=payload.symbol,
            action=payload.signal,
            entry_price=payload.entry_price,
            quantity=payload.quantity,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            trailing_stop=payload.trailing_stop,
            breakeven_enabled=True
        )

        print(
            Fore.LIGHTGREEN_EX +
            "[EXECUTION]" +
            Style.RESET_ALL +
            f" OPEN BUY "
            f"{payload.symbol} "
            f"@ {payload.entry_price} "
            f"| qty={payload.quantity}"
        )

        metrics = self.metrics.get_metrics(
            user_id=payload.user_id
        )

        print(
            Fore.LIGHTBLUE_EX +
            "[PORTFOLIO]" +
            Style.RESET_ALL +
            f" Trades={metrics['total_trades']} "
            f"| Winrate={metrics['winrate']} "
            f"| PnL={metrics['pnl']}"
        )