# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent

from core.contracts.messages import (
    StrategySignalMessage,
    RiskDecisionMessage,
    RiskDecisionPayload
)

from data.storage.positions_repository import (
    get_open_position
)


class RiskAgent(BaseAgent):

    def on_message(self, message):

        if not isinstance(message, StrategySignalMessage):
            return

        payload = message.payload

        user_id = message.user_id

        symbol = payload.symbol
        signal = payload.signal

        price = payload.price
        atr = payload.atr

        position = get_open_position(
            user_id,
            symbol
        )

        approved = False
        action = "HOLD"

        quantity = 2.0

        stop_loss = None
        take_profit = None
        trailing_stop = None

        # ==========================================
        # OPEN POSITION
        # ==========================================

        if position is None and signal == "BUY":

            approved = True
            action = "OPEN"

            stop_loss = round(
                price - (atr * 2),
                2
            )

            take_profit = round(
                price + (atr * 4),
                2
            )

            trailing_stop = stop_loss

        # ==========================================
        # MANAGE POSITION
        # ==========================================

        elif position is not None:

            entry_price = position["entry_price"]

            current_sl = position["stop_loss"]

            # ======================================
            # BREAKEVEN
            # ======================================

            risk = (
                entry_price
                - current_sl
            )

            breakeven_price = (
                entry_price
                + risk
            )

            if (
                price >= breakeven_price
                and not position["breakeven_enabled"]
            ):

                current_sl = entry_price

            # ======================================
            # TRAILING STOP
            # ======================================

            trailing_candidate = round(
                price - (atr * 2),
                2
            )

            if trailing_candidate > current_sl:
                current_sl = trailing_candidate

            # ======================================
            # EXIT RULES
            # ======================================

            if (
                price <= current_sl
                or price >= position["take_profit"]
            ):

                approved = True
                action = "CLOSE"

            stop_loss = current_sl
            trailing_stop = current_sl

        self.bus.publish(
            RiskDecisionMessage(
                user_id=user_id,
                payload=RiskDecisionPayload(
                    symbol=symbol,

                    action=action,
                    approved=approved,

                    price=price,
                    quantity=quantity,

                    stop_loss=stop_loss,
                    take_profit=take_profit,

                    trailing_stop=trailing_stop,

                    atr=atr,

                    breakeven_enabled=True
                )
            )
        )