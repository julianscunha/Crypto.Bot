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

        symbol = message.payload.symbol
        price = message.payload.price

        key = f"{user_id}:{symbol}"

        if key not in self.price_history:
            self.price_history[key] = []

        history = self.price_history[key]

        history.append(price)

        history[:] = history[-100:]

        if len(history) < 30:
            return

        ema9 = ema(history, 9)
        ema21 = ema(history, 21)

        rsi14 = rsi(history, 14)
        atr14 = atr(history, 14)

        if None in [ema9, ema21, rsi14, atr14]:
            return

        signal = None

        if ema9 > ema21 and rsi14 > 55:
            signal = "BUY"

        elif ema9 < ema21 and rsi14 < 45:
            signal = "SELL"

        if signal is None:
            return

        current_tick = len(history)

        last_tick = self.cooldown.get(key, 0)

        if current_tick - last_tick < 5:
            return

        self.cooldown[key] = current_tick

        self.bus.publish(
            StrategySignalMessage(
                user_id=user_id,
                payload=StrategySignalPayload(
                    symbol=symbol,
                    signal=signal,
                    price=price,
                    atr=atr14
                )
            )
        )