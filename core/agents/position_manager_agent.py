# -*- coding: utf-8 -*-

from colorama import (
    Fore,
    Style,
    init
)

from core.contracts.messages import (
    MarketDataMessage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from services.position_lifecycle_service import (
    PositionLifecycleService
)

init(autoreset=True)


class PositionManagerAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = trades_repository

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            MarketDataMessage
        ):
            return

        payload = message.payload

        positions = self.positions.get_open_trades(
            user_id=payload.user_id
        )

        for trade in positions:

            if trade.symbol != payload.symbol:
                continue

            # =====================================================
            # UNREALIZED PNL
            # =====================================================

            unrealized_pnl = (
                PositionLifecycleService
                .calculate_unrealized_pnl(
                    entry_price=trade.entry_price,
                    current_price=payload.close,
                    quantity=trade.quantity
                )
            )

            # =====================================================
            # UPDATE TRADE
            # =====================================================

            trade = (
                self.positions.update_trade_price(
                    trade_id=trade.id,
                    current_price=payload.close,
                    unrealized_pnl=unrealized_pnl
                )
            )

            if not trade:
                continue

            # =====================================================
            # TRAILING STOP
            # =====================================================

            trailing_price = (
                PositionLifecycleService
                .update_trailing_stop(
                    current_price=payload.close,
                    highest_price=trade.highest_price,
                    trailing_percent=0.02
                )
            )

            # =====================================================
            # STOP LOSS
            # =====================================================

            if payload.close <= trade.stop_loss:

                self.positions.close_trade(
                    trade_id=trade.id,
                    exit_price=payload.close,
                    pnl=trade.unrealized_pnl,
                    reason="STOP_LOSS"
                )

                print(
                    Fore.LIGHTRED_EX +
                    "[POSITION]" +
                    Style.RESET_ALL +
                    f" STOP LOSS "
                    f"{trade.symbol} "
                    f"PnL={round(trade.unrealized_pnl, 2)}"
                )

            # =====================================================
            # TAKE PROFIT
            # =====================================================

            elif payload.close >= trade.take_profit:

                self.positions.close_trade(
                    trade_id=trade.id,
                    exit_price=payload.close,
                    pnl=trade.unrealized_pnl,
                    reason="TAKE_PROFIT"
                )

                print(
                    Fore.CYAN +
                    "[POSITION]" +
                    Style.RESET_ALL +
                    f" TAKE PROFIT "
                    f"{trade.symbol} "
                    f"PnL={round(trade.unrealized_pnl, 2)}"
                )

            # =====================================================
            # TRAILING STOP
            # =====================================================

            elif payload.close <= trailing_price:

                self.positions.close_trade(
                    trade_id=trade.id,
                    exit_price=payload.close,
                    pnl=trade.unrealized_pnl,
                    reason="TRAILING_STOP"
                )

                print(
                    Fore.YELLOW +
                    "[POSITION]" +
                    Style.RESET_ALL +
                    f" TRAILING STOP "
                    f"{trade.symbol} "
                    f"PnL={round(trade.unrealized_pnl, 2)}"
                )