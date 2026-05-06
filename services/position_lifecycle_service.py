# -*- coding: utf-8 -*-


class PositionLifecycleService:

    @staticmethod
    def calculate_unrealized_pnl(
        entry_price: float,
        current_price: float,
        quantity: float
    ):

        return (
            current_price - entry_price
        ) * quantity

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