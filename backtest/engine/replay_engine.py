# -*- coding: utf-8 -*-

import asyncio
import pandas as pd

from core.bus.event_bus import EventBus

from core.agents.analyst_agent import AnalystAgent
from core.agents.strategy_agent import StrategyAgent
from core.agents.risk_agent import RiskAgent
from core.agents.execution_agent import ExecutionAgent
from core.agents.position_manager_agent import PositionManagerAgent

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)

from data.storage.database import init_db


class ReplayEngine:

    def __init__(
        self,
        csv_path: str,
        user_id: int = 999
    ):

        self.csv_path = csv_path

        self.user_id = user_id

        self.bus = EventBus()

        init_db()

        AnalystAgent(self.bus)

        StrategyAgent(self.bus)

        RiskAgent(self.bus)

        ExecutionAgent(self.bus)

        PositionManagerAgent(self.bus)

    async def replay(self):

        df = pd.read_csv(
            self.csv_path
        )

        for _, row in df.iterrows():

            payload = (
                MarketDataPayload(
                    user_id=self.user_id,
                    symbol=row["symbol"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"]
                )
            )

            message = (
                MarketDataMessage(
                    sender="ReplayEngine",
                    payload=payload
                )
            )

            await self.bus.publish(
                message
            )

            await asyncio.sleep(0.001)