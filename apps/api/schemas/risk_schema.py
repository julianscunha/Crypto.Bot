# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

from typing import (
    Optional
)

from pydantic import (
    BaseModel
)

# =====================================================
# RISK STATUS RESPONSE
# =====================================================
#
# Surfaces core/services/risk_protection_service.py's daily circuit
# breaker state -- max_daily_loss_percent and max_daily_trades,
# which previously existed as unused config values with no
# enforcement anywhere. trading_halted=true means the bot will not
# open new positions for the rest of the current UTC day, regardless
# of how good the next signal looks.

class RiskStatusResponse(
    BaseModel
):

    trading_halted: bool

    halt_reason: Optional[str]

    daily_pnl: float

    daily_loss_percent: float

    max_daily_loss_percent: float

    daily_trade_count: int

    max_daily_trades: int

    day_started_at: datetime
