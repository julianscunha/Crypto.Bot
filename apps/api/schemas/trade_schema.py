# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TradeResponse(BaseModel):

    id: int

    symbol: str

    action: str

    entry_price: float

    current_price: float

    quantity: float

    pnl: float

    status: str

    unrealized_pnl: Optional[float] = None

    realized_pnl: Optional[float] = None

    exit_reason: Optional[str] = None

    created_at: Optional[datetime] = None

    closed_at: Optional[datetime] = None