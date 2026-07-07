# -*- coding: utf-8 -*-

from statistics import (
    mean
)

from core.config.indicators_config import (
    INDICATORS_CONFIG
)

# =====================================================
# HELPERS
# =====================================================

def safe_float(
    value,
    fallback=0.0
):

    try:

        return float(value)

    except Exception:

        return fallback


def validate_period(
    period
):

    try:

        period = int(period)

        return period > 0

    except Exception:

        return False


def validate_series(
    values,
    minimum_length=1
):

    if not values:

        return False

    return len(values) >= minimum_length

# =====================================================
# EMA
# =====================================================

def ema(
    values,
    period=None
):

    if period is None:

        period = (
            INDICATORS_CONFIG[
                "default_ema_period"
            ]
        )

    # =================================================
    # VALIDATION
    # =================================================

    if not validate_period(
        period
    ):

        return None

    if not validate_series(
        values,
        period
    ):

        return None

    multiplier = (
        2 / (period + 1)
    )

    ema_value = (
        mean(values[:period])
    )

    for price in values[period:]:

        price = safe_float(
            price
        )

        ema_value = (

            (
                price
                -
                ema_value
            )

            * multiplier

        ) + ema_value

    return round(
        ema_value,
        8
    )

# =====================================================
# RSI
# =====================================================

def rsi(
    values,
    period=None
):

    if period is None:

        period = (
            INDICATORS_CONFIG[
                "default_rsi_period"
            ]
        )

    # =================================================
    # VALIDATION
    # =================================================

    if not validate_period(
        period
    ):

        return None

    if not validate_series(
        values,
        period + 1
    ):

        return None

    gains = []

    losses = []

    for index in range(
        1,
        len(values)
    ):

        current = safe_float(
            values[index]
        )

        previous = safe_float(
            values[index - 1]
        )

        delta = (
            current
            -
            previous
        )

        if delta >= 0:

            gains.append(
                delta
            )

        else:

            losses.append(
                abs(delta)
            )

    epsilon = (
        INDICATORS_CONFIG[
            "division_safety_epsilon"
        ]
    )

    avg_gain = (
        mean(gains[-period:])
        if gains
        else epsilon
    )

    avg_loss = (
        mean(losses[-period:])
        if losses
        else epsilon
    )

    if avg_loss <= 0:

        return 100.0

    rs = (
        avg_gain
        /
        avg_loss
    )

    rsi_value = (
        100
        -
        (
            100
            /
            (
                1 + rs
            )
        )
    )

    return round(
        rsi_value,
        4
    )

# =====================================================
# ATR
# =====================================================

def atr(
    values,
    period=None
):

    if period is None:

        period = (
            INDICATORS_CONFIG[
                "default_atr_period"
            ]
        )

    # =================================================
    # VALIDATION
    # =================================================

    if not validate_period(
        period
    ):

        return None

    if not validate_series(
        values,
        period + 1
    ):

        return None

    true_ranges = []

    for index in range(
        1,
        len(values)
    ):

        current = safe_float(
            values[index]
        )

        previous = safe_float(
            values[index - 1]
        )

        tr = abs(
            current
            -
            previous
        )

        true_ranges.append(
            tr
        )

    if not true_ranges:

        return None

    atr_value = (
        mean(
            true_ranges[-period:]
        )
    )

    return round(
        atr_value,
        8
    )
