# -*- coding: utf-8 -*-

from copy import deepcopy

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
)

# =====================================================
# CONFIG REGISTRY
# =====================================================
#
# RiskAgent reads atr_stop_multiplier/atr_take_profit_multiplier
# from TRADING_CONFIG, but atr_trailing_multiplier from
# TRADE_MANAGEMENT_CONFIG. The optimizer tunes all three together,
# so every optimizer param must be routed to whichever config dict
# actually owns it, or tuning silently has no effect.

_CONFIG_REGISTRY = (

    TRADING_CONFIG,

    TRADE_MANAGEMENT_CONFIG
)


def _dict_owning_key(key):

    for config in _CONFIG_REGISTRY:

        if key in config:

            return config

    # Unknown keys default to TRADING_CONFIG so they are at least
    # visible/inspectable, rather than silently dropped.

    return TRADING_CONFIG


def get_config_snapshot():

    return {

        "trading_config": deepcopy(
            TRADING_CONFIG
        ),

        "trade_management_config": deepcopy(
            TRADE_MANAGEMENT_CONFIG
        )
    }


def apply_config(
    params: dict
):

    for key, value in params.items():

        target = _dict_owning_key(
            key
        )

        target[key] = value


def restore_config(
    snapshot: dict
):

    TRADING_CONFIG.clear()

    TRADING_CONFIG.update(
        snapshot["trading_config"]
    )

    TRADE_MANAGEMENT_CONFIG.clear()

    TRADE_MANAGEMENT_CONFIG.update(
        snapshot["trade_management_config"]
    )