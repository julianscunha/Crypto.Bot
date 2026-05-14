# -*- coding: utf-8 -*-

from core.contracts.messages import (
    RiskDecisionMessage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from data.storage.metrics import (
    MetricsStorage
)

from core.services.signal_quality_service import (
    signal_quality_service
)

from colorama import (
    Fore,
    Style,
    init
)

from core.utils.console_logger import (
    log
)

class ExecutionAgent:

    def __init__(self, bus):

        self.bus = bus

        self.signal_quality = (
            signal_quality_service
        )

        self.positions = (
            trades_repository
        )

        self.metrics = (
            MetricsStorage()
        )

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            RiskDecisionMessage
        ):
            return

        payload = message.payload

        # =====================================================
        # SIGNAL FILTER
        # =====================================================

        if payload.signal != "BUY":
            return

        # =====================================================
        # EXISTING POSITION
        # =====================================================

        if self.positions.has_open_trade(
            payload.user_id,
            payload.symbol
        ):
                    
            log(
                "EXECUTION BLOCKED",
                f"{payload.symbol} | POSITION_ALREADY_OPEN",
                Fore.LIGHTRED_EX
            )

            return

        # =====================================================
        # CREATE TRADE
        # =====================================================

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

        # =====================================================
        # EXECUTION LOG
        # =====================================================     
        
        log(
            "EXECUTION",
            f"OPEN BUY {payload.symbol} @ {payload.entry_price} | qty={payload.quantity}",
            Fore.LIGHTGREEN_EX
        )

        # =====================================================
        # COOLDOWN REGISTER
        # =====================================================

        self.signal_quality.register_trade(
            payload.user_id,
            payload.symbol
        )

        # =====================================================
        # PORTFOLIO
        # =====================================================

        metrics = (
            self.metrics.get_metrics(
                user_id=payload.user_id
            )
        )
        
        log(
            "PORTFOLIO",
            f"Trades={metrics['total_trades']} | Winrate={metrics['winrate']} | PnL={metrics['pnl']}",
            Fore.LIGHTBLUE_EX
        )