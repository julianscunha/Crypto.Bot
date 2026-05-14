# -*- coding: utf-8 -*-

from pydantic import BaseModel


class MetricsResponse(BaseModel):

    total_trades: int

    winrate: float

    pnl: float