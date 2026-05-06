# -*- coding: utf-8 -*-

from statistics import mean


def ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    ema_value = mean(values[:period])

    for price in values[period:]:
        ema_value = (price - ema_value) * multiplier + ema_value

    return ema_value


def rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]

        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    avg_gain = mean(gains[-period:]) if gains else 0.0001
    avg_loss = mean(losses[-period:]) if losses else 0.0001

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def atr(values, period=14):

    if len(values) < period + 1:
        return None

    trs = []

    for i in range(1, len(values)):
        tr = abs(values[i] - values[i - 1])
        trs.append(tr)

    return mean(trs[-period:])