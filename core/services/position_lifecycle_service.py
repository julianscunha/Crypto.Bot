# -*- coding: utf-8 -*-

from core.config.exchange_config import (
    EXCHANGE_CONFIG
)


class PositionLifecycleService:

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _is_valid_price(
        price: float
    ) -> bool:

        return (
            price is not None
            and
            price > 0
        )

    @staticmethod
    def _is_valid_quantity(
        quantity: float
    ) -> bool:

        return (
            quantity is not None
            and
            quantity > 0
        )

    @staticmethod
    def _round_price(
        value: float
    ) -> float:

        precision = (
            EXCHANGE_CONFIG[
                "price_precision"
            ]
        )

        return round(
            value,
            precision
        )

    @staticmethod
    def _calculate_fee(
        price: float,
        quantity: float,
        fee_percent: float
    ) -> float:

        return (
            price
            *
            quantity
            *
            fee_percent
        )

    # =====================================================
    # UNREALIZED PNL
    # =====================================================

    @classmethod
    def calculate_unrealized_pnl(
        cls,
        entry_price: float,
        current_price: float,
        quantity: float
    ) -> float:

        # =================================================
        # SAFETY
        # =================================================

        if not cls._is_valid_price(
            entry_price
        ):

            return 0.0

        if not cls._is_valid_price(
            current_price
        ):

            return 0.0

        if not cls._is_valid_quantity(
            quantity
        ):

            return 0.0

        # =================================================
        # GROSS PNL
        # =================================================

        gross_pnl = (

            current_price
            -
            entry_price

        ) * quantity

        # =================================================
        # FEES
        # =================================================

        if EXCHANGE_CONFIG[
            "enable_fee_simulation"
        ]:

            taker_fee_percent = (
                EXCHANGE_CONFIG[
                    "taker_fee_percent"
                ]
            )

            entry_fee = (
                cls._calculate_fee(

                    entry_price,

                    quantity,

                    taker_fee_percent
                )
            )

            exit_fee = (
                cls._calculate_fee(

                    current_price,

                    quantity,

                    taker_fee_percent
                )
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

    @classmethod
    def apply_entry_slippage(
        cls,
        entry_price: float
    ) -> float:

        if not cls._is_valid_price(
            entry_price
        ):

            return 0.0

        if not EXCHANGE_CONFIG[
            "enable_slippage_simulation"
        ]:

            return cls._round_price(
                entry_price
            )

        slippage_percent = (
            EXCHANGE_CONFIG[
                "entry_slippage_percent"
            ]
        )

        adjusted_price = (

            entry_price

            * (

                1 + slippage_percent
            )
        )

        return cls._round_price(
            adjusted_price
        )

    # =====================================================
    # EXIT SLIPPAGE
    # =====================================================

    @classmethod
    def apply_exit_slippage(
        cls,
        exit_price: float
    ) -> float:

        if not cls._is_valid_price(
            exit_price
        ):

            return 0.0

        if not EXCHANGE_CONFIG[
            "enable_slippage_simulation"
        ]:

            return cls._round_price(
                exit_price
            )

        slippage_percent = (
            EXCHANGE_CONFIG[
                "exit_slippage_percent"
            ]
        )

        adjusted_price = (

            exit_price

            * (

                1 - slippage_percent
            )
        )

        return cls._round_price(
            adjusted_price
        )

    # =====================================================
    # NET PNL
    # =====================================================

    @classmethod
    def calculate_net_pnl(
        cls,
        entry_price: float,
        exit_price: float,
        quantity: float
    ) -> float:

        return cls.calculate_unrealized_pnl(

            entry_price=entry_price,

            current_price=exit_price,

            quantity=quantity
        )
