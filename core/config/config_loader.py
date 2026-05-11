# -*- coding: utf-8 -*-

import json

from pathlib import Path

from core.config.trading_config import (
    TRADING_CONFIG
)


BEST_CONFIG_PATH = (
    "core/config/best_config.json"
)


def load_best_config():

    path = Path(
        BEST_CONFIG_PATH
    )

    if not path.exists():
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

    print()

    print(
        "[CONFIG LOADER]",
        "Best config loaded"
    )

    print(
        TRADING_CONFIG
    )