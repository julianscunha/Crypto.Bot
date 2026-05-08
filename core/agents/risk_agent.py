# -*- coding: utf-8 -*-

from core.contracts.messages import (
    StrategySignalMessage,
    RiskDecisionMessage,
    RiskDecisionPayload
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)


class RiskAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = trades_repository

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            StrategySignalMessage
        ):
            return

        payload = message.payload

        print(
            Fore.LIGHTYELLOW_EX +
            "[RISK]" +
            Style.RESET_ALL +
            f" {payload.symbol}"
        )

        # =====================================================
        # SIGNAL FILTER
        # =====================================================

        if payload.signal != "BUY":

            print(
                Fore.LIGHTRED_EX +
                "[RISK BLOCKED]" +
                Style.RESET_ALL +
                f" {payload.symbol} "
                f"| INVALID_SIGNAL"
            )

            return

        # =====================================================
        # EXISTING POSITION
        # =====================================================

        existing_position = (
            self.positions.get_open_trade(
                user_id=payload.user_id,
                symbol=payload.symbol
            )
        )

        if existing_position:

            print(
                Fore.LIGHTRED_EX +
                "[RISK BLOCKED]" +
                Style.RESET_ALL +
                f" {payload.symbol} "
                f"| POSITION_ALREADY_OPEN"
            )

            return

        # =====================================================
        # RISK CALCULATION
        # =====================================================

        entry_price = payload.entry_price

        stop_loss = round(
            entry_price * 0.98,
            2
        )

        take_profit = round(
            entry_price * 1.02,
            2
        )

        trailing_stop = round(
            entry_price * 0.015,
            4
        )

        quantity = 2.0

        # =====================================================
        # PAYLOAD
        # =====================================================

        decision_payload = (
            RiskDecisionPayload(
                user_id=payload.user_id,
                symbol=payload.symbol,
                signal=payload.signal,
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                risk_reward=2.0
            )
        )

        decision_message = (
            RiskDecisionMessage(
                sender="RiskAgent",
                payload=decision_payload
            )
        )

        # =====================================================
        # PUBLISH
        # =====================================================

        print(
            Fore.LIGHTGREEN_EX +
            "[RISK APPROVED]" +
            Style.RESET_ALL +
            f" {payload.symbol}"
        )

        await self.bus.publish(
            decision_message
        )