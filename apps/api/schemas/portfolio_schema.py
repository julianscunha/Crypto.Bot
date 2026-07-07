# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import BaseModel


class PortfolioResponse(BaseModel):

    balance: float

    equity: float

    realized_pnl: float

    unrealized_pnl: float

    total_pnl: float

    open_positions: int

    closed_positions: int

    exposure: float

    drawdown: float

    created_at: datetime
