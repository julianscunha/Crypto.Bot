# -*- coding: utf-8 -*-

import json

from pathlib import Path

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
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

    # =====================================================
    # PARAMS
    # =====================================================
    #
    # OptimizerEngine writes best_config.json as a flat dict of
    # params (json.dump(best_result["params"], f, ...)), not wrapped
    # under a "params" key. Support both shapes defensively.

    params = (
        data.get("params", data)
        if isinstance(data, dict)
        else {}
    )

    # =====================================================
    # ROUTE PARAMS TO THE CONFIG THAT OWNS EACH KEY
    # =====================================================
    #
    # atr_trailing_multiplier belongs to TRADE_MANAGEMENT_CONFIG;
    # everything else the optimizer tunes belongs to TRADING_CONFIG.

    for key, value in params.items():

        if key in TRADE_MANAGEMENT_CONFIG:

            TRADE_MANAGEMENT_CONFIG[key] = value

        else:

            TRADING_CONFIG[key] = value

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
            f"TS={TRADE_MANAGEMENT_CONFIG['atr_trailing_multiplier']}"
        )
    )

    log(
        "SYSTEM",
        (
            "RISK CONFIG "
            f"RISK={TRADING_CONFIG['risk_per_trade_percent']}% "
            f"BALANCE={TRADING_CONFIG['account_balance']}"
        )
    )

    log(
        "SYSTEM",
        (
            "STRUCTURE CONFIG "
            f"MIN_CANDLES="
            f"{TRADING_CONFIG['minimum_structure_candles']}"
        )
    )