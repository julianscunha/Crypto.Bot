# -*- coding: utf-8 -*-

import json

from pathlib import Path

from core.config.trading_config import (
    TRADING_CONFIG
)


class RegimeConfigLoader:

    def __init__(self):

        self.current_regime = None

    # =====================================================
    # LOAD REGIME CONFIG
    # =====================================================

    def load_regime(
        self,
        regime: str
    ):

        if regime == self.current_regime:
            return

        if regime == "UNKNOWN":
            return

        path = Path(
            f"core/config/regimes/{regime.lower()}.json"
        )

        if not path.exists():

            print(
                "[REGIME CONFIG]",
                "Config not found",
                regime
            )

            return

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            config = json.load(f)

        TRADING_CONFIG.update(
            config
        )

        self.current_regime = regime

        print()

        print(
            "[REGIME CONFIG LOADED]",
            regime
        )

        print(
            TRADING_CONFIG
        )


regime_config_loader = (
    RegimeConfigLoader()
)
