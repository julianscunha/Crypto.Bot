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

        self.trades = TradesRepository()

        self.portfolio = PortfolioRepository()

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

        realized_pnl = sum(
            trade.realized_pnl or 0.0
            for trade in closed_trades
        )

        unrealized_pnl = sum(
            trade.unrealized_pnl or 0.0
            for trade in open_trades
        )

        total_pnl = (
            realized_pnl +
            unrealized_pnl
        )

        balance = (
            initial_balance +
            realized_pnl
        )

        equity = (
            balance +
            unrealized_pnl
        )

        exposure = sum(
            (
                trade.current_price or 0.0
            ) * (
                trade.quantity or 0.0
            )
            for trade in open_trades
        )

        peak_equity = max(
            equity,
            initial_balance
        )

        drawdown = round(
            (
                (
                    peak_equity -
                    equity
                ) / peak_equity
            ) * 100,
            2
        )

        snapshot = (
            self.portfolio.create_snapshot(
                user_id=user_id,
                balance=round(balance, 2),
                equity=round(equity, 2),
                realized_pnl=round(realized_pnl, 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                total_pnl=round(total_pnl, 2),
                open_positions=len(open_trades),
                closed_positions=len(closed_trades),
                exposure=round(exposure, 2),
                drawdown=drawdown
            )
        )
        
        log(
            "PORTFOLIO",
            f"Equity={snapshot.equity} | Exposure={snapshot.exposure} | RealizedPnL={snapshot.realized_pnl}| UnrealizedPnL={snapshot.unrealized_pnl} | Drawdown={snapshot.drawdown}%", Fore.LIGHTWHITE_EX)

        return snapshot
