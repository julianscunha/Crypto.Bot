# -*- coding: utf-8 -*-

"""
Regression tests for core/services/position_lifecycle_service.py

Bug fixed: EXCHANGE_CONFIG key names didn't match what
PositionLifecycleService read (use_fees/taker_fee/use_slippage/slippage
vs the real enable_fee_simulation/taker_fee_percent/
enable_slippage_simulation/entry_slippage_percent/exit_slippage_percent).
This caused a KeyError on every single unrealized PnL calculation and
every trade entry, meaning no trade could ever be opened or marked to
market.
"""

from core.services.position_lifecycle_service import (
    PositionLifecycleService
)

from core.config.exchange_config import (
    EXCHANGE_CONFIG
)


class TestCalculateUnrealizedPnl:

    def test_does_not_raise_keyerror(self):

        result = PositionLifecycleService.calculate_unrealized_pnl(
            entry_price=100.0,
            current_price=105.0,
            quantity=1.0
        )

        assert isinstance(result, float)

    def test_long_position_profit(self):

        pnl = PositionLifecycleService.calculate_unrealized_pnl(
            entry_price=100.0,
            current_price=110.0,
            quantity=2.0
        )

        # gross movement: (110-100)*2 = 20, minus fee simulation
        assert pnl > 0

    def test_long_position_loss(self):

        pnl = PositionLifecycleService.calculate_unrealized_pnl(
            entry_price=100.0,
            current_price=90.0,
            quantity=1.0
        )

        assert pnl < 0

    def test_fee_simulation_reduces_pnl_when_enabled(self):

        original = EXCHANGE_CONFIG["enable_fee_simulation"]

        try:

            EXCHANGE_CONFIG["enable_fee_simulation"] = False

            pnl_no_fees = (
                PositionLifecycleService
                .calculate_unrealized_pnl(
                    entry_price=100.0,
                    current_price=110.0,
                    quantity=1.0
                )
            )

            EXCHANGE_CONFIG["enable_fee_simulation"] = True

            pnl_with_fees = (
                PositionLifecycleService
                .calculate_unrealized_pnl(
                    entry_price=100.0,
                    current_price=110.0,
                    quantity=1.0
                )
            )

            assert pnl_with_fees < pnl_no_fees

        finally:

            EXCHANGE_CONFIG["enable_fee_simulation"] = original


class TestApplyEntrySlippage:

    def test_does_not_raise_keyerror(self):

        result = PositionLifecycleService.apply_entry_slippage(
            entry_price=100.0
        )

        assert isinstance(result, float)

    def test_slippage_disabled_returns_same_price(self):

        original = EXCHANGE_CONFIG["enable_slippage_simulation"]

        try:

            EXCHANGE_CONFIG["enable_slippage_simulation"] = False

            result = (
                PositionLifecycleService
                .apply_entry_slippage(
                    entry_price=100.0
                )
            )

            assert result == 100.0

        finally:

            EXCHANGE_CONFIG[
                "enable_slippage_simulation"
            ] = original

    def test_slippage_enabled_moves_price_against_entry(self):

        original = EXCHANGE_CONFIG["enable_slippage_simulation"]

        try:

            EXCHANGE_CONFIG["enable_slippage_simulation"] = True

            result = (
                PositionLifecycleService
                .apply_entry_slippage(
                    entry_price=100.0
                )
            )

            # entering long: slippage should make entry slightly
            # worse (higher), never better
            assert result >= 100.0

        finally:

            EXCHANGE_CONFIG[
                "enable_slippage_simulation"
            ] = original


class TestApplyExitSlippage:

    def test_does_not_raise_keyerror(self):

        result = PositionLifecycleService.apply_exit_slippage(
            exit_price=100.0
        )

        assert isinstance(result, float)

    def test_slippage_enabled_moves_price_against_exit(self):

        original = EXCHANGE_CONFIG["enable_slippage_simulation"]

        try:

            EXCHANGE_CONFIG["enable_slippage_simulation"] = True

            result = (
                PositionLifecycleService
                .apply_exit_slippage(
                    exit_price=100.0
                )
            )

            # exiting a long: slippage should make exit slightly
            # worse (lower), never better
            assert result <= 100.0

        finally:

            EXCHANGE_CONFIG[
                "enable_slippage_simulation"
            ] = original


class TestCalculateNetPnl:

    def test_returns_float(self):

        result = PositionLifecycleService.calculate_net_pnl(
            entry_price=100.0,
            exit_price=110.0,
            quantity=1.0
        )

        assert isinstance(result, float)
