# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketDataMessage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.services.position_lifecycle_service import (
    PositionLifecycleService
)

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
)

from core.utils.console_logger import (
    log
)


class PositionManagerAgent:

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        self.positions = (
            trades_repository
        )

        self.lifecycle = (
            PositionLifecycleService
        )

        self.config = (
            TRADE_MANAGEMENT_CONFIG
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
            MarketDataMessage
        ):

            return

        payload = (
            message.payload
        )

        open_positions = (

            self.positions.get_open_trades(
                user_id=payload.user_id
            )
        )

        for trade in open_positions:

            if trade.symbol != payload.symbol:

                continue

            self._process_position(

                trade=trade,

                market_price=payload.close
            )

    # =====================================================
    # PROCESS POSITION
    # =====================================================

    def _process_position(
        self,
        trade,
        market_price: float
    ):

        # =================================================
        # UNREALIZED PNL
        # =================================================

        unrealized_pnl = (

            self.lifecycle
            .calculate_unrealized_pnl(

                entry_price=trade.entry_price,

                current_price=market_price,

                quantity=trade.quantity
            )
        )

        # =================================================
        # UPDATE TRADE
        # =================================================

        managed_trade = (

            self.positions
            .update_trade_price(

                trade_id=trade.id,

                current_price=market_price,

                unrealized_pnl=unrealized_pnl
            )
        )

        if not managed_trade:

            return

        # =================================================
        # TRAILING STOP
        # =================================================

        trailing_stop_price = (
            self._calculate_trailing_stop_price(
                managed_trade
            )
        )

        pnl = round(

            managed_trade.unrealized_pnl,

            2
        )

        # =================================================
        # STOP LOSS
        # =================================================

        if market_price <= managed_trade.stop_loss:

            self._close_position(

                managed_trade,

                market_price,

                "STOP_LOSS",

                pnl,

                "ERROR"
            )

            return

        # =================================================
        # TAKE PROFIT
        # =================================================

        if market_price >= managed_trade.take_profit:

            self._close_position(

                managed_trade,

                market_price,

                "TAKE_PROFIT",

                pnl,

                "SUCCESS"
            )

            return

        # =================================================
        # TRAILING STOP
        # =================================================

        if market_price <= trailing_stop_price:

            self._close_position(

                managed_trade,

                market_price,

                "TRAILING_STOP",

                pnl,

                "WARNING"
            )

    # =====================================================
    # TRAILING STOP
    # =====================================================

    def _calculate_trailing_stop_price(
        self,
        trade
    ):

        if not self.config[
            "enable_trailing_stop"
        ]:

            return float("-inf")

        if trade.highest_price is None:

            return float("-inf")

        trailing_distance = (
            trade.trailing_stop
        )

        return (

            trade.highest_price
            -
            trailing_distance
        )

    # =====================================================
    # CLOSE POSITION
    # =====================================================

    def _close_position(
        self,
        trade,
        exit_price: float,
        reason: str,
        pnl: float,
        log_level: str
    ):

        self.positions.close_trade(

            trade_id=trade.id,

            exit_price=exit_price,

            pnl=trade.unrealized_pnl,

            reason=reason
        )

        log(
            "POSITION",
            f"{reason} pnl={pnl}",
            log_level
        )