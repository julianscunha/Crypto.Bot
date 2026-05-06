import asyncio

from core.workroom.bus import WorkRoomBus
from data.storage.database import init_db
from core.agents.analyst_agent import AnalystAgent
from core.agents.strategy_agent import StrategyAgent
from core.agents.risk_agent import RiskAgent
from core.agents.execution_agent import ExecutionAgent

from data.ingestion.binance_ws import BinanceWS


async def main():
    init_db()
    bus = WorkRoomBus()

    # Agents
    AnalystAgent("analyst", bus)
    StrategyAgent("strategy", bus)
    RiskAgent("risk", bus)
    ExecutionAgent("execution", bus)

    ws = BinanceWS(bus, user_id=0)

    await ws.start()


if __name__ == "__main__":
    asyncio.run(main())