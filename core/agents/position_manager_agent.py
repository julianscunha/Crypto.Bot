# -*- coding: utf-8 -*-

from datetime import datetime

from core.contracts.messages import (
    MarketDataMessage
)

from data.storage.positions_repository import (
    PositionsRepository
)

from services.position_lifecycle_service import (
    PositionLifecycleService
)


class PositionManagerAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = PositionsRepository()

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(message, MarketDataMessage):
            return

        payload = message.payload

        positions = self.positions.get_open_positions(
            user_id=payload.user_id
        )

        for trade in positions:

            if trade.symbol != payload.symbol:
                continue

            trade.current_price = payload.close

            trade.unrealized_pnl = (
                PositionLifecycleService
                .calculate_unrealized_pnl(
                    entry_price=trade.entry_price,
                    current_price=payload.close,
                    quantity=trade.quantity
                )
            )

            if (
                trade.highest_price is None or
                payload.close > trade.highest_price
            ):
                trade.highest_price = payload.close

            trailing_price = (
                PositionLifecycleService
                .update_trailing_stop(
                    current_price=payload.close,
                    highest_price=trade.highest_price,
                    trailing_percent=0.02
                )
            )

            if payload.close <= trade.stop_loss:

                self.positions.close_position(
                    trade_id=trade.id,
                    exit_price=payload.close,
                    pnl=trade.unrealized_pnl,
                    reason="STOP_LOSS"
                )

                print(
                    f"[POSITION] STOP LOSS "
                    f"{trade.symbol} "
                    f"PnL={round(trade.unrealized_pnl, 2)}"
                )

            elif payload.close >= trade.take_profit:

                self.positions.close_position(
                    trade_id=trade.id,
                    exit_price=payload.close,
                    pnl=trade.unrealized_pnl,
                    reason="TAKE_PROFIT"
                )

                print(
                    f"[POSITION] TAKE PROFIT "
                    f"{trade.symbol} "
                    f"PnL={round(trade.unrealized_pnl, 2)}"
                )

            elif payload.close <= trailing_price:

                self.positions.close_position(
                    trade_id=trade.id,
                    exit_price=payload.close,
                    pnl=trade.unrealized_pnl,
                    reason="TRAILING_STOP"
                )

                print(
                    f"[POSITION] TRAILING STOP "
                    f"{trade.symbol} "
                    f"PnL={round(trade.unrealized_pnl, 2)}"
                )