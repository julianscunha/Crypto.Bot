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

from core.utils.console_logger import (
    log
)

from core.services.position_lifecycle_service import (
    PositionLifecycleService
)

from core.config.trading_config import (
    TRADING_CONFIG
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
        # EXECUTION MODE
        # =====================================================

        paper_execution = (
            TRADING_CONFIG[
                "paper_execution"
            ]
        )

        # =====================================================
        # SIGNAL FILTER
        # =====================================================

        if payload.signal != "BUY":

            log(
                "EXECUTION",
                (
                    f"BLOCKED "
                    f"{payload.symbol} "
                    f"| INVALID_SIGNAL"
                ),
                "ERROR"
            )

            return

        # =====================================================
        # EXISTING POSITION
        # =====================================================

        if self.positions.has_open_trade(
            payload.user_id,
            payload.symbol
        ):

            log(
                "EXECUTION",
                (
                    f"BLOCKED "
                    f"{payload.symbol} "
                    f"| POSITION_ALREADY_OPEN"
                ),
                "ERROR"
            )

            return

        # =====================================================
        # CREATE TRADE
        # =====================================================

        entry_price = (
            PositionLifecycleService
            .apply_entry_slippage(
                payload.entry_price
            )
        )

        self.positions.create_trade(
            user_id=payload.user_id,
            symbol=payload.symbol,
            action=payload.signal,
            entry_price=entry_price,
            quantity=payload.quantity,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            trailing_stop=payload.trailing_stop,
            breakeven_enabled=True
        )

        # =====================================================
        # EXECUTION LOG
        # =====================================================

        execution_mode = (
            "PAPER"
            if paper_execution
            else "LIVE"
        )

        log(
            "EXECUTION",
            (
                f"{execution_mode} OPEN BUY "
                f"{payload.symbol} "
                f"@ {entry_price} "
                f"| qty={payload.quantity}"
            ),
            "SUCCESS"
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
            "POSITION",
            (
                f"PORTFOLIO "
                f"trades={metrics['total_trades']} "
                f"| winrate={metrics['winrate']} "
                f"| pnl={metrics['pnl']}"
            )
        )