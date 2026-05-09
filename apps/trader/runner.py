import asyncio

from core.bus.event_bus import EventBus

from core.agents.analyst_agent import AnalystAgent

from core.agents.strategy_agent import StrategyAgent

from core.agents.risk_agent import RiskAgent

from core.agents.execution_agent import ExecutionAgent

from core.agents.position_manager_agent import (
    PositionManagerAgent
)

from data.ingestion.binance_ws import (
    BinanceWS
)

from data.storage.database import (
    init_db
)


DEFAULT_USER_ID = 0

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT"
]


async def main():

    init_db()

    bus = EventBus()

    AnalystAgent(bus)

    StrategyAgent(bus)

    RiskAgent(bus)

    ExecutionAgent(bus)

    PositionManagerAgent(bus)

    ws = BinanceWS(
        bus=bus,
        user_id=DEFAULT_USER_ID
    )

    await ws.start()


if __name__ == "__main__":

    asyncio.run(main())