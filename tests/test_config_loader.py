# -*- coding: utf-8 -*-

"""
Regression tests for core/config/config_loader.py

Bugs fixed:
1. load_best_config() read data.get("params", {}), but the optimizer
   actually writes best_config.json as a flat params dict with no
   "params" wrapper -> always loaded an empty dict, silently.
2. It referenced TRADING_CONFIG['atr_trailing_multiplier'], which does
   not exist in TRADING_CONFIG (it lives in TRADE_MANAGEMENT_CONFIG)
   -> guaranteed KeyError whenever best_config.json existed.
3. It referenced TRADING_CONFIG['min_structure_candles'], but the real
   key is 'minimum_structure_candles' -> guaranteed KeyError.
"""

import json

import pytest

from core.config import config_loader

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
)


@pytest.fixture
def isolated_best_config_path(tmp_path, monkeypatch):

    path = tmp_path / "best_config.json"

    monkeypatch.setattr(
        config_loader,
        "BEST_CONFIG_PATH",
        str(path)
    )

    return path


class TestLoadBestConfig:

    def test_missing_file_does_not_raise(
        self,
        isolated_best_config_path
    ):

        # file deliberately not created

        config_loader.load_best_config()

    def test_flat_params_file_loads_without_keyerror(
        self,
        isolated_best_config_path
    ):

        isolated_best_config_path.write_text(
            json.dumps({
                "atr_take_profit_multiplier": 3.0,
                "atr_stop_multiplier": 1.5,
                "atr_trailing_multiplier": 0.5
            })
        )

        snapshot_stop = TRADING_CONFIG["atr_stop_multiplier"]

        snapshot_trailing = (
            TRADE_MANAGEMENT_CONFIG["atr_trailing_multiplier"]
        )

        try:

            config_loader.load_best_config()

            assert (
                TRADING_CONFIG["atr_take_profit_multiplier"]
                == 3.0
            )

            assert (
                TRADING_CONFIG["atr_stop_multiplier"]
                == 1.5
            )

            assert (
                TRADE_MANAGEMENT_CONFIG[
                    "atr_trailing_multiplier"
                ]
                == 0.5
            )

        finally:

            TRADING_CONFIG["atr_stop_multiplier"] = (
                snapshot_stop
            )

            TRADE_MANAGEMENT_CONFIG[
                "atr_trailing_multiplier"
            ] = snapshot_trailing

    def test_wrapped_params_file_also_supported(
        self,
        isolated_best_config_path
    ):

        # defensive: also support the {"params": {...}} shape in case
        # a future writer uses it

        isolated_best_config_path.write_text(
            json.dumps({
                "params": {
                    "atr_stop_multiplier": 1.9
                }
            })
        )

        snapshot_stop = TRADING_CONFIG["atr_stop_multiplier"]

        try:

            config_loader.load_best_config()

            assert (
                TRADING_CONFIG["atr_stop_multiplier"]
                == 1.9
            )

        finally:

            TRADING_CONFIG["atr_stop_multiplier"] = (
                snapshot_stop
            )

    def test_does_not_crash_on_minimum_structure_candles_log(
        self,
        isolated_best_config_path
    ):

        # this previously crashed with KeyError on
        # TRADING_CONFIG['min_structure_candles'] (wrong key name)
        # every single time the file existed, regardless of its
        # contents

        isolated_best_config_path.write_text(
            json.dumps({
                "atr_stop_multiplier": 1.5
            })
        )

        config_loader.load_best_config()

        assert "minimum_structure_candles" in TRADING_CONFIG
