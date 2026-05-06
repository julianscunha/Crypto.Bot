# -*- coding: utf-8 -*-

from core.agents.base_agent import BaseAgent

from core.contracts.messages import (
    MarketDataMessage,
    StrategySignalMessage,
    StrategySignalPayload
)

from data.features.indicators import (
    ema,
    rsi,
    atr
)


class StrategyAgent(BaseAgent):

    def __init__(self, name, bus):

        super().__init__(name, bus)

        self.price_history = {}
        self.cooldown = {}

    def on_message(self, message):

        if not isinstance(message, MarketDataMessage):
            return

        user_id = message.user_id
        price = message.payload.price

        if user_id not in self.price_history:
            self.price_history[user_id] = []

        history = self.price_history[user_id]

        history.append(price)

        # mantém histórico enxuto
        history[:] = history[-100:]

        # precisa de dados suficientes
        if len(history) < 30:
            return

        ema9 = ema(history, 9)
        ema21 = ema(history, 21)
        rsi14 = rsi(history, 14)
        atr14 = atr(history, 14)

        if None in [ema9, ema21, rsi14, atr14]:
            return

        # ==========================================
        # VOLATILITY FILTER
        # ==========================================

        if atr14 < 0.3:
            return

        # ==========================================
        # COOLDOWN
        # ==========================================

        current_tick = len(history)

        last_trade_tick = self.cooldown.get(user_id, 0)

        if current_tick - last_trade_tick < 5:
            return

        signal = None

        # ==========================================
        # LONG TREND
        # ==========================================

        if (
            ema9 > ema21
            and rsi14 > 55
        ):
            signal = "BUY"

        # ==========================================
        # SHORT TREND
        # ==========================================

        elif (
            ema9 < ema21
            and rsi14 < 45
        ):
            signal = "SELL"

        if signal is None:
            return

        self.cooldown[user_id] = current_tick

        self.bus.publish(
            StrategySignalMessage(
                user_id=user_id,
                payload=StrategySignalPayload(
                    signal=signal,
                    price=price
                )
            )
        )