# -*- coding: utf-8 -*-

from core.contracts.messages import (
    RiskDecisionMessage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.services.trade_metrics_service import (
    trade_metrics_service
)

from core.services.signal_quality_service import (
    signal_quality_service
)

from core.services.position_lifecycle_service import (
    PositionLifecycleService
)

from core.services.execution_router import (
    execution_router
)

from core.utils.console_logger import (
    log
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.state.market_state import (
    market_state
)


class ExecutionAgent:

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        self.positions = (
            trades_repository
        )

        self.signal_quality = (
            signal_quality_service
        )

        self.trade_metrics = (
            trade_metrics_service
        )

        self.position_lifecycle = (
            PositionLifecycleService
        )

        self.execution_router = (
            execution_router
        )

        self.execution_mode = (
            TRADING_CONFIG[
                "runtime_mode"
            ]
        )

        self.bus.subscribe(
            self
        )

    # =====================================================
    # MESSAGE
    # =====================================================

    async def on_message(
        self,
        message
    ):

        if not isinstance(
            message,
            RiskDecisionMessage
        ):

            return

        payload = (
            message.payload
        )

        # =================================================
        # EXECUTION VALIDATION
        # =================================================

        valid, reason = (
            self._validate_execution(
                payload
            )
        )

        if not valid:

            market_state.register_rejected_signal(
                reason
            )

            log(
                "EXECUTION",
                f"BLOCKED {reason}",
                "WARNING"
            )

            return

        # =================================================
        # EXECUTION (PAPER OR LIVE -- DECIDED BY THE ROUTER)
        # =================================================

        execution_result = (

            await self.execution_router
            .execute(
                payload
            )
        )

        if not execution_result.success:

            market_state.register_rejected_signal(
                execution_result.reason
            )

            log(
                "EXECUTION",
                f"BLOCKED {execution_result.reason}",
                "ERROR"
            )

            return

        created_trade = (
            execution_result.trade
        )

        executed_entry_price = (
            created_trade.entry_price
        )

        # =================================================
        # EXECUTION TELEMETRY
        # =================================================

        market_state.register_approved_signal()

        market_state.register_order_execution(
            self.execution_mode
        )

        # =================================================
        # SIGNAL COOLDOWN
        # =================================================

        self.signal_quality.register_trade(

            payload.user_id,

            payload.symbol
        )

        # =================================================
        # EXECUTION LOG
        # =================================================

        log(
            "EXECUTION",
            (
                f"{self.execution_mode} "
                f"{payload.signal} "
                f"entry={executed_entry_price} "
                f"qty={payload.quantity}"
            ),
            "SUCCESS"
        )

        # =================================================
        # PORTFOLIO METRICS
        # =================================================

        portfolio_metrics = (

            self.trade_metrics
            .get_metrics(

                user_id=payload.user_id
            )
        )

        log(
            "PORTFOLIO",
            (
                f"open={portfolio_metrics['open_positions']} "
                f"pnl={portfolio_metrics['pnl']}"
            )
        )

    # =====================================================
    # EXECUTION VALIDATION
    # =====================================================

    def _validate_execution(
        self,
        payload
    ):

        # =================================================
        # SIGNAL
        # =================================================

        if payload.signal != "BUY":

            return (
                False,
                "INVALID_SIGNAL"
            )

        # =================================================
        # DUPLICATED POSITION
        # =================================================

        if self.positions.has_open_trade(

            payload.user_id,

            payload.symbol
        ):

            return (
                False,
                "POSITION_ALREADY_OPEN"
            )

        # =================================================
        # ENTRY PRICE
        # =================================================

        if payload.entry_price <= 0:

            return (
                False,
                "INVALID_ENTRY_PRICE"
            )

        # =================================================
        # POSITION SIZE
        # =================================================

        if payload.quantity <= 0:

            return (
                False,
                "INVALID_POSITION_SIZE"
            )

        # =================================================
        # STOP LOSS
        # =================================================

        if payload.stop_loss <= 0:

            return (
                False,
                "INVALID_STOP_LOSS"
            )

        # =================================================
        # TAKE PROFIT
        # =================================================

        if payload.take_profit <= 0:

            return (
                False,
                "INVALID_TAKE_PROFIT"
            )

        # =================================================
        # RISK STRUCTURE
        # =================================================

        if payload.stop_loss >= payload.entry_price:

            return (
                False,
                "INVALID_STOP_STRUCTURE"
            )

        if payload.take_profit <= payload.entry_price:

            return (
                False,
                "INVALID_TARGET_STRUCTURE"
            )

        return (
            True,
            "VALID"
        )