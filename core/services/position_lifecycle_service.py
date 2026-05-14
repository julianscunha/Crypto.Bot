# -*- coding: utf-8 -*-

from core.config.exchange_config import (
    EXCHANGE_CONFIG
)


class PositionLifecycleService:

    @staticmethod
    def calculate_unrealized_pnl(
        entry_price: float,
        current_price: float,
        quantity: float
    ):

        gross_pnl = (
            current_price - entry_price
        ) * quantity

        # =====================================================
        # FEES
        # =====================================================

        if EXCHANGE_CONFIG["use_fees"]:

            fee_percent = (
                EXCHANGE_CONFIG[
                    "taker_fee"
                ]
            )

            entry_fee = (
                entry_price
                * quantity
                * fee_percent
            )

            exit_fee = (
                current_price
                * quantity
                * fee_percent
            )

            gross_pnl -= (
                entry_fee + exit_fee
            )

        return round(
            gross_pnl,
            2
        )

    @staticmethod
    def apply_entry_slippage(
        entry_price: float
    ) -> float:

        if not EXCHANGE_CONFIG[
            "use_slippage"
        ]:
            return entry_price

        slippage = (
            EXCHANGE_CONFIG[
                "slippage"
            ]
        )

        return round(
            entry_price * (
                1 + slippage
            ),
            2
        )

    @staticmethod
    def apply_exit_slippage(
        exit_price: float
    ) -> float:

        if not EXCHANGE_CONFIG[
            "use_slippage"
        ]:
            return exit_price

        slippage = (
            EXCHANGE_CONFIG[
                "slippage"
            ]
        )

        return round(
            exit_price * (
                1 - slippage
            ),
            2
        )

    @staticmethod
    def update_trailing_stop(
        current_price: float,
        highest_price: float,
        trailing_percent: float
    ):

        return (
            highest_price *
            (1 - trailing_percent)
        )