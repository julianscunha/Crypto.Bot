# -*- coding: utf-8 -*-

from sqlalchemy.orm import (
    Session
)

from sqlalchemy import (
    func,
    case
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    Trade
)

from core.services.trade_analytics import (
    compute_equity_curve_stats,
    compute_profit_factor,
    compute_risk_reward,
    compute_recovery_factor,
    compute_sharpe_ratio,
    compute_sortino_ratio
)


class TradeMetricsService:

    def __init__(
        self
    ):

        pass

    # =====================================================
    # SESSION
    # =====================================================

    def _session(
        self
    ) -> Session:

        return SessionLocal()

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _safe_float(
        value,
        precision: int = 2
    ):

        return round(

            float(value or 0.0),

            precision
        )

    @staticmethod
    def _safe_percentage(
        numerator,
        denominator,
        precision: int = 2
    ):

        if denominator <= 0:

            return 0.0

        return round(

            (
                numerator
                / denominator
            ) * 100,

            precision
        )

    # =====================================================
    # CLOSED TRADE METRICS
    # =====================================================

    def get_metrics(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            # =================================================
            # CLOSED TRADES
            # =================================================

            result = (

                session.query(

                    func.count(
                        Trade.id
                    ),

                    func.sum(

                        case(
                            (
                                Trade.pnl > 0,
                                1
                            ),
                            else_=0
                        )
                    ),

                    func.sum(

                        case(
                            (
                                Trade.pnl < 0,
                                1
                            ),
                            else_=0
                        )
                    ),

                    func.sum(
                        Trade.pnl
                    ),

                    func.avg(
                        Trade.pnl
                    ),

                    func.max(
                        Trade.pnl
                    ),

                    func.min(
                        Trade.pnl
                    )
                )

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "CLOSED"
                )

                .first()
            )

            total_trades = (
                result[0] or 0
            )

            winning_trades = (
                result[1] or 0
            )

            losing_trades = (
                result[2] or 0
            )

            total_pnl = (
                self._safe_float(
                    result[3]
                )
            )

            average_trade_pnl = (
                self._safe_float(
                    result[4]
                )
            )

            best_trade_pnl = (
                self._safe_float(
                    result[5]
                )
            )

            worst_trade_pnl = (
                self._safe_float(
                    result[6]
                )
            )

            # =================================================
            # WIN RATE
            # =================================================

            winrate = (
                self._safe_percentage(

                    winning_trades,

                    total_trades
                )
            )

            # =================================================
            # OPEN POSITIONS
            # =================================================

            open_positions = (

                session.query(

                    func.count(
                        Trade.id
                    )
                )

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "OPEN"
                )

                .scalar()
            )

            # =================================================
            # OPEN EXPOSURE
            # =================================================

            open_exposure = (

                session.query(

                    func.sum(

                        Trade.current_price
                        *
                        Trade.quantity
                    )
                )

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "OPEN"
                )

                .scalar()
            )

            open_exposure = (
                self._safe_float(
                    open_exposure
                )
            )

            # =================================================
            # EXPECTANCY
            # =================================================

            expectancy = 0.0

            if total_trades > 0:

                expectancy = round(

                    total_pnl
                    /
                    total_trades,

                    2
                )

            # =================================================
            # RESPONSE
            # =================================================

            return {

                # =============================================
                # CORE
                # =============================================

                "total_trades":
                    total_trades,

                "winning_trades":
                    winning_trades,

                "losing_trades":
                    losing_trades,

                "winrate":
                    winrate,

                # =============================================
                # PNL
                # =============================================

                "pnl":
                    total_pnl,

                "average_trade_pnl":
                    average_trade_pnl,

                "best_trade_pnl":
                    best_trade_pnl,

                "worst_trade_pnl":
                    worst_trade_pnl,

                "expectancy":
                    expectancy,

                # =============================================
                # EXPOSURE
                # =============================================

                "open_positions":
                    open_positions or 0,

                "open_exposure":
                    open_exposure
            }

        finally:

            session.close()

    # =====================================================
    # OPEN EXPOSURE
    # =====================================================

    def get_open_exposure(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            exposure = (

                session.query(

                    func.sum(

                        Trade.current_price
                        *
                        Trade.quantity
                    )
                )

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "OPEN"
                )

                .scalar()
            )

            return self._safe_float(
                exposure
            )

        finally:

            session.close()

    # =====================================================
    # ADVANCED METRICS (RISK-ADJUSTED RETURN, STREAKS)
    # =====================================================
    #
    # Distinct from get_metrics() above: that one answers "how is
    # this account doing right now" (winrate, PnL, open exposure).
    # This answers "how consistent/risky is this trading strategy
    # over its full history" -- Sharpe/Sortino, the true historical
    # max drawdown (peak-to-trough across ALL closed trades ever,
    # not the session-scoped drawdown PortfolioService tracks for
    # circuit-breaker purposes), and win/loss streaks. Computed via
    # core.services.trade_analytics, the same pure functions
    # backtest/engine/metrics_engine.py uses, so live and backtest
    # numbers are never computed by two different, silently
    # drifting implementations.

    def get_advanced_metrics(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            closed_trades = (

                session.query(
                    Trade
                )

                .filter(

                    Trade.user_id == user_id,

                    Trade.status == "CLOSED"
                )

                .order_by(
                    Trade.closed_at.asc()
                )

                .all()
            )

        finally:

            session.close()

        pnls = [
            trade.pnl or 0.0
            for trade in closed_trades
        ]

        curve_stats = (
            compute_equity_curve_stats(
                pnls
            )
        )

        wins = (
            curve_stats["wins"]
        )

        losses = (
            curve_stats["losses"]
        )

        total_pnl = (
            self._safe_float(
                sum(pnls)
            )
        )

        return {

            "sharpe_ratio":
                compute_sharpe_ratio(
                    pnls
                ),

            "sortino_ratio":
                compute_sortino_ratio(
                    pnls
                ),

            "max_drawdown":
                curve_stats["max_drawdown"],

            "profit_factor":
                compute_profit_factor(
                    wins,
                    losses
                ),

            "risk_reward":
                compute_risk_reward(
                    wins,
                    losses
                ),

            "recovery_factor":
                compute_recovery_factor(
                    total_pnl,
                    curve_stats["max_drawdown"]
                ),

            "max_win_streak":
                curve_stats["max_win_streak"],

            "max_loss_streak":
                curve_stats["max_loss_streak"],

            "current_win_streak":
                curve_stats["current_win_streak"],

            "current_loss_streak":
                curve_stats["current_loss_streak"],

            "sample_size":
                len(pnls)
        }

    # =====================================================
    # PERFORMANCE SUMMARY
    # =====================================================

    def get_performance_summary(
        self,
        user_id: int
    ):

        metrics = self.get_metrics(
            user_id
        )

        return {

            "winrate":
                metrics["winrate"],

            "expectancy":
                metrics["expectancy"],

            "pnl":
                metrics["pnl"],

            "open_exposure":
                metrics["open_exposure"],

            "total_trades":
                metrics["total_trades"]
        }


trade_metrics_service = (
    TradeMetricsService()
)
