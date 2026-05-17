# -*- coding: utf-8 -*-

from data.storage.repositories.trades_repository import (
    TradesRepository
)

from data.storage.repositories.portfolio_repository import (
    PortfolioRepository
)

from core.utils.console_logger import (
    log
)


class PortfolioService:

    def __init__(self):

        self.trades = (
            TradesRepository()
        )

        self.portfolio = (
            PortfolioRepository()
        )

    # =====================================================
    # BUILD SNAPSHOT
    # =====================================================

    def build_snapshot(
        self,
        user_id: int,
        initial_balance: float = 1000.0
    ):

        open_trades = (
            self.trades.get_open_trades(
                user_id=user_id
            )
        )

        closed_trades = (
            self.trades.get_closed_trades(
                user_id=user_id
            )
        )

        # =================================================
        # REALIZED PNL
        # =================================================

        realized_pnl = round(

            sum(

                trade.realized_pnl or 0.0

                for trade in closed_trades
            ),

            2
        )

        # =================================================
        # UNREALIZED PNL
        # =================================================

        unrealized_pnl = round(

            sum(

                trade.unrealized_pnl or 0.0

                for trade in open_trades
            ),

            2
        )

        # =================================================
        # TOTAL PNL
        # =================================================

        total_pnl = round(
            realized_pnl
            +
            unrealized_pnl,
            2
        )

        # =================================================
        # BALANCE
        # =================================================

        balance = round(
            initial_balance
            +
            realized_pnl,
            2
        )

        # =================================================
        # EQUITY
        # =================================================

        equity = round(
            balance
            +
            unrealized_pnl,
            2
        )

        # =================================================
        # EXPOSURE
        # =================================================

        exposure = round(

            sum(

                (
                    trade.current_price or 0.0
                )

                *

                (
                    trade.quantity or 0.0
                )

                for trade in open_trades
            ),

            2
        )

        # =================================================
        # DRAWDOWN
        # =================================================

        peak_reference = max(
            initial_balance,
            balance
        )

        if peak_reference <= 0:

            drawdown = 0.0

        else:

            drawdown = round(

                (
                    (
                        peak_reference
                        -
                        equity
                    )

                    / peak_reference
                ) * 100,

                2
            )

        # =================================================
        # SNAPSHOT
        # =================================================

        snapshot = (
            self.portfolio.create_snapshot(

                user_id=user_id,

                balance=balance,

                equity=equity,

                realized_pnl=realized_pnl,

                unrealized_pnl=unrealized_pnl,

                total_pnl=total_pnl,

                open_positions=len(
                    open_trades
                ),

                closed_positions=len(
                    closed_trades
                ),

                exposure=exposure,

                drawdown=drawdown
            )
        )

        # =================================================
        # PORTFOLIO LOG
        # =================================================

        log(
            "PORTFOLIO",
            (
                f"EQUITY={snapshot.equity} "
                f"PNL={snapshot.total_pnl} "
                f"DD={snapshot.drawdown}%"
            )
        )

        return snapshot