# -*- coding: utf-8 -*-

import json

from pathlib import Path

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.utils.console_logger import (
    log
)


BEST_CONFIG_PATH = (
    "core/config/best_config.json"
)


def load_best_config():

    path = Path(
        BEST_CONFIG_PATH
    )

    if not path.exists():

        log(
            "SYSTEM",
            "BEST CONFIG NOT FOUND",
            "WARNING"
        )

        return

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    params = data.get(
        "params",
        {}
    )

    TRADING_CONFIG.update(
        params
    )

    # =====================================================
    # CONFIG LOGS
    # =====================================================

    log(
        "SYSTEM",
        "BEST CONFIG LOADED",
    )

    log(
        "SYSTEM",
        (
            "ATR CONFIG "
            f"SL={TRADING_CONFIG['atr_stop_multiplier']} "
            f"TP={TRADING_CONFIG['atr_take_profit_multiplier']} "
            f"TS={TRADING_CONFIG['atr_trailing_multiplier']}"
        )
    )

    log(
        "SYSTEM",
        (
            "RISK CONFIG "
            f"RR={TRADING_CONFIG['risk_reward_ratio']} "
            f"QTY={TRADING_CONFIG['default_quantity']}"
        )
    )

    log(
        "SYSTEM",
        (
            "STRUCTURE CONFIG "
            f"MIN_CANDLES="
            f"{TRADING_CONFIG['min_structure_candles']}"
        )
    )