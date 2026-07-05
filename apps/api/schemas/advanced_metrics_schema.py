# -*- coding: utf-8 -*-

from pydantic import (
    BaseModel
)

# =====================================================
# ADVANCED METRICS RESPONSE
# =====================================================
#
# Separate from MetricsResponse (the existing "account status right
# now" shape used by /metrics and /dashboard): this answers "how
# consistent/risky has this strategy been over its full trade
# history" -- Sharpe/Sortino, true historical max drawdown (distinct
# from the session-scoped drawdown PortfolioResponse.drawdown
# tracks), and win/loss streaks. See
# core/services/trade_analytics.py for the underlying calculations,
# shared with the backtest engine.

class AdvancedMetricsResponse(
    BaseModel
):

    sharpe_ratio: float

    sortino_ratio: float

    max_drawdown: float

    profit_factor: float

    risk_reward: float

    recovery_factor: float

    max_win_streak: int

    max_loss_streak: int

    current_win_streak: int

    current_loss_streak: int

    sample_size: int
