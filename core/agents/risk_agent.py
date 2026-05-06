# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent

from core.contracts.messages import (
    StrategySignalMessage,
    RiskDecisionMessage,
    RiskDecisionPayload
)

from data.storage.positions_repository import get_open_position

from data.features.indicators import atr


RISK_PROFILES = {
    "conservative": {
        "risk_per_trade": 0.01,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp": 3.0
    },
    "balanced": {
        "risk_per_trade": 0.02,
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp": 4.0
    },
    "aggressive": {
        "risk_per_trade": 0.05,
        "atr_multiplier_sl": 3.0,
        "atr_multiplier_tp": 6.0
    }
}


class RiskAgent(BaseAgent):

    def __init__(self, name, bus):

        super().__init__(name, bus)

        self.user_profiles = {}
        self.price_history = {}

    def get_profile(self, user_id):
        return self.user_profiles.get(user_id, "balanced")

    def on_message(self, message):

        if not isinstance(message, StrategySignalMessage):
            return

        user_id = message.user_id
        signal = message.payload.signal
        price = message.payload.price

        if user_id not in self.price_history:
            self.price_history[user_id] = []

        self.price_history[user_id].append(price)

        history = self.price_history[user_id]

        atr14 = atr(history, 14)

        if atr14 is None:
            return

        profile = RISK_PROFILES[self.get_profile(user_id)]

        position = get_open_position(user_id)

        approved = False
        action = "HOLD"

        stop_loss = None
        take_profit = None

        risk_amount = 1000 * profile["risk_per_trade"]

        quantity = risk_amount / atr14

        # ==========================================
        # OPEN
        # ==========================================

        if position is None and signal == "BUY":

            approved = True
            action = "OPEN"

            stop_loss = (
                price
                - (atr14 * profile["atr_multiplier_sl"])
            )

            take_profit = (
                price
                + (atr14 * profile["atr_multiplier_tp"])
            )

        # ==========================================
        # MANAGE
        # ==========================================

        elif position is not None:

            entry = position["price"]

            sl = (
                entry
                - (atr14 * profile["atr_multiplier_sl"])
            )

            tp = (
                entry
                + (atr14 * profile["atr_multiplier_tp"])
            )

            if price <= sl or price >= tp:

                approved = True
                action = "CLOSE"

        self.bus.publish(
            RiskDecisionMessage(
                user_id=user_id,
                payload=RiskDecisionPayload(
                    action=action,
                    approved=approved,
                    price=price,
                    quantity=round(quantity, 4),
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            )
        )