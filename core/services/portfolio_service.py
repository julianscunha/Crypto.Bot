# -*- coding: utf-8 -*-

from data.storage.repositories.trades_repository import (
    TradesRepository
)

from data.storage.repositories.portfolio_repository import (
    PortfolioRepository
)

from core.services.trade_metrics_service import (
    trade_metrics_service
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.utils.console_logger import (
    log
)


class PortfolioService:

    def __init__(self):

        self.trades_repository = (
            TradesRepository()
        )

        self.portfolio_repository = (
            PortfolioRepository()
        )

        self.trade_metrics = (
            trade_metrics_service
        )

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _safe_round(
        value: float
    ) -> float:

        return round(
            float(value or 0.0),
            2
        )

    @staticmethod
    def _calculate_drawdown_percent(
        peak_equity: float,
        current_equity: float
    ) -> float:

        if peak_equity <= 0:

            return 0.0

        drawdown = (

            (
                peak_equity
                -
                current_equity
            )

            / peak_equity
        ) * 100

        return round(
            max(drawdown, 0.0),
            2
        )

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def build_snapshot(
        self,
        user_id: int,
        initial_balance: float | None = None
    ):

        # =================================================
        # CONFIG
        # =================================================

        if initial_balance is None:

            initial_balance = (
                TRADING_CONFIG[
                    "account_balance"
                ]
            )

        # =================================================
        # TRADES
        # =================================================

        open_trades = (

            self.trades_repository
            .get_open_trades(
                user_id=user_id
            )
        )

        closed_trades = (

            self.trades_repository
            .get_closed_trades(
                user_id=user_id
            )
        )

        # =================================================
        # REALIZED PNL
        # =================================================

        realized_pnl = self._safe_round(

            sum(

                trade.realized_pnl or 0.0

                for trade in closed_trades
            )
        )

        # =================================================
        # UNREALIZED PNL
        # =================================================

        unrealized_pnl = self._safe_round(

            sum(

                trade.unrealized_pnl or 0.0

                for trade in open_trades
            )
        )

        # =================================================
        # TOTAL PNL
        # =================================================

        total_pnl = self._safe_round(

            realized_pnl
            +
            unrealized_pnl
        )

        # =================================================
        # BALANCE
        # =================================================

        balance = self._safe_round(

            initial_balance
            +
            realized_pnl
        )

        # =================================================
        # EQUITY
        # =================================================

        equity = self._safe_round(

            balance
            +
            unrealized_pnl
        )

        # =================================================
        # OPEN EXPOSURE
        # =================================================

        open_exposure = (

            self.trade_metrics
            .get_open_exposure(
                user_id=user_id
            )
        )

        # =================================================
        # PEAK EQUITY
        # =================================================

        peak_equity = max(
            initial_balance,
            balance,
            equity
        )

        # =================================================
        # DRAWDOWN
        # =================================================

        drawdown_percent = (

            self._calculate_drawdown_percent(

                peak_equity,

                equity
            )
        )

        # =================================================
        # SNAPSHOT
        # =================================================

        portfolio_snapshot = (

            self.portfolio_repository
            .create_snapshot(

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

                exposure=open_exposure,

                drawdown=drawdown_percent
            )
        )

        # =================================================
        # TELEMETRY
        # =================================================

        log(
            "PORTFOLIO",
            (
                f"EQUITY={portfolio_snapshot.equity} "
                f"BALANCE={portfolio_snapshot.balance} "
                f"PNL={portfolio_snapshot.total_pnl} "
                f"DD={portfolio_snapshot.drawdown}%"
            )
        )

        return portfolio_snapshot


portfolio_service = (
    PortfolioService()
)