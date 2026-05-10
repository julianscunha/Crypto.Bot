# -*- coding: utf-8 -*-

from copy import deepcopy

from core.config.trading_config import (
    TRADING_CONFIG
)


def get_config_snapshot():

    return deepcopy(
        TRADING_CONFIG
    )


def apply_config(
    params: dict
):

    TRADING_CONFIG.update(
        params
    )


def restore_config(
    snapshot: dict
):

    TRADING_CONFIG.clear()

    TRADING_CONFIG.update(
        snapshot
    )