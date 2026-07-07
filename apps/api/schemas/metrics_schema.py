# -*- coding: utf-8 -*-

from pydantic import (
    BaseModel
)

# =====================================================
# METRICS RESPONSE
# =====================================================

class MetricsResponse(
    BaseModel
):

    # =================================================
    # CORE METRICS
    # =================================================

    total_trades: int

    winning_trades: int

    losing_trades: int

    winrate: float

    # =================================================
    # PNL ANALYTICS
    # =================================================

    pnl: float

    average_trade_pnl: float

    best_trade_pnl: float

    worst_trade_pnl: float

    expectancy: float

    # =================================================
    # EXPOSURE
    # =================================================

    open_positions: int

    open_exposure: float
