# -*- coding: utf-8 -*-

"""
Regression tests for backtest/optimizer/config_runtime.py

Bug fixed: apply_config() wrote atr_trailing_multiplier into
TRADING_CONFIG, but RiskAgent actually reads it from
TRADE_MANAGEMENT_CONFIG. This meant the optimizer's trailing-stop
tuning silently never took effect on the agent that uses it.
"""

from backtest.optimizer.config_runtime import (
    get_config_snapshot,
    apply_config,
    restore_config
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
)


class TestApplyConfig:

    def test_atr_trailing_multiplier_routes_to_trade_management_config(self):

        snapshot = get_config_snapshot()

        try:

            apply_config({
                "atr_trailing_multiplier": 0.42
            })

            assert (
                TRADE_MANAGEMENT_CONFIG[
                    "atr_trailing_multiplier"
                ]
                ==
                0.42
            )

        finally:

            restore_config(snapshot)

    def test_atr_stop_multiplier_routes_to_trading_config(self):

        snapshot = get_config_snapshot()

        try:

            apply_config({
                "atr_stop_multiplier": 1.77
            })

            assert (
                TRADING_CONFIG[
                    "atr_stop_multiplier"
                ]
                ==
                1.77
            )

        finally:

            restore_config(snapshot)

    def test_mixed_params_route_to_correct_configs(self):

        snapshot = get_config_snapshot()

        try:

            apply_config({
                "atr_take_profit_multiplier": 3.3,
                "atr_stop_multiplier": 1.1,
                "atr_trailing_multiplier": 0.6
            })

            assert (
                TRADING_CONFIG["atr_take_profit_multiplier"]
                == 3.3
            )

            assert (
                TRADING_CONFIG["atr_stop_multiplier"]
                == 1.1
            )

            assert (
                TRADE_MANAGEMENT_CONFIG["atr_trailing_multiplier"]
                == 0.6
            )

        finally:

            restore_config(snapshot)


class TestRestoreConfig:

    def test_restore_reverts_both_configs(self):

        snapshot = get_config_snapshot()

        original_stop = TRADING_CONFIG["atr_stop_multiplier"]

        original_trailing = (
            TRADE_MANAGEMENT_CONFIG["atr_trailing_multiplier"]
        )

        apply_config({
            "atr_stop_multiplier": 9.9,
            "atr_trailing_multiplier": 9.9
        })

        restore_config(snapshot)

        assert (
            TRADING_CONFIG["atr_stop_multiplier"]
            == original_stop
        )

        assert (
            TRADE_MANAGEMENT_CONFIG["atr_trailing_multiplier"]
            == original_trailing
        )


class TestGetConfigSnapshot:

    def test_snapshot_is_independent_copy(self):

        snapshot = get_config_snapshot()

        TRADING_CONFIG["atr_stop_multiplier"] = 123.0

        assert (
            snapshot["trading_config"]["atr_stop_multiplier"]
            != 123.0
        )

        restore_config(snapshot)
