# -*- coding: utf-8 -*-

from core.config.exchange_config import (
    EXCHANGE_CONFIG
)


class PositionLifecycleService:

    # =====================================================
    # UNREALIZED PNL
    # =====================================================

    @staticmethod
    def calculate_unrealized_pnl(
        entry_price: float,
        current_price: float,
        quantity: float
    ):

        # =================================================
        # SAFETY
        # =================================================

        if entry_price <= 0:

            return 0.0

        if current_price <= 0:

            return 0.0

        if quantity <= 0:

            return 0.0

        gross_pnl = (

            current_price
            -
            entry_price

        ) * quantity

        # =================================================
        # FEES
        # =================================================

        if EXCHANGE_CONFIG[
            "use_fees"
        ]:

            fee_percent = (
                EXCHANGE_CONFIG[
                    "taker_fee"
                ]
            )

            entry_fee = (

                entry_price
                *
                quantity
                *
                fee_percent
            )

            exit_fee = (

                current_price
                *
                quantity
                *
                fee_percent
            )

            gross_pnl -= (
                entry_fee
                +
                exit_fee
            )

        return round(
            gross_pnl,
            2
        )

    # =====================================================
    # ENTRY SLIPPAGE
    # =====================================================

    @staticmethod
    def apply_entry_slippage(
        entry_price: float
    ) -> float:

        # =================================================
        # SAFETY
        # =================================================

        if entry_price <= 0:

            return 0.0

        if not EXCHANGE_CONFIG[
            "use_slippage"
        ]:

            return round(
                entry_price,
                2
            )

        slippage = (
            EXCHANGE_CONFIG[
                "slippage"
            ]
        )

        adjusted_price = (

            entry_price

            * (

                1 + slippage
            )
        )

        return round(
            adjusted_price,
            2
        )

    # =====================================================
    # EXIT SLIPPAGE
    # =====================================================

    @staticmethod
    def apply_exit_slippage(
        exit_price: float
    ) -> float:

        # =================================================
        # SAFETY
        # =================================================

        if exit_price <= 0:

            return 0.0

        if not EXCHANGE_CONFIG[
            "use_slippage"
        ]:

            return round(
                exit_price,
                2
            )

        slippage = (
            EXCHANGE_CONFIG[
                "slippage"
            ]
        )

        adjusted_price = (

            exit_price

            * (

                1 - slippage
            )
        )

        return round(
            adjusted_price,
            2
        )