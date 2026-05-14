# -*- coding: utf-8 -*-

from typing import List

from pydantic import BaseModel

from apps.api.schemas.metrics_schema import (
    MetricsResponse
)

from apps.api.schemas.portfolio_schema import (
    PortfolioResponse
)

from apps.api.schemas.trade_schema import (
    TradeResponse
)


class RuntimeResponse(BaseModel):

    websocket_connected: bool

    total_messages: int

    active_symbols: List[str]


class DashboardResponse(BaseModel):

    runtime: RuntimeResponse

    metrics: MetricsResponse

    portfolio: PortfolioResponse

    open_trades: List[TradeResponse]

    recent_closed_trades: List[TradeResponse]