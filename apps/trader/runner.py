# -*- coding: utf-8 -*-

from core.bus.event_bus import EventBus

from core.agents.analyst_agent import AnalystAgent
from core.agents.strategy_agent import StrategyAgent
from core.agents.risk_agent import RiskAgent
from core.agents.execution_agent import ExecutionAgent

from data.ingestion.binance_ws import BinanceWS
from data.storage.database import init_db


async def main():

    # =========================
    # INIT DATABASE
    # =========================

    init_db()

    # =========================
    # EVENT BUS
    # =========================

    bus = EventBus()

    # =========================
    # AGENTS
    # =========================

    analyst = AnalystAgent("analyst", bus)
    strategy = StrategyAgent("strategy", bus)
    risk = RiskAgent("risk", bus)
    execution = ExecutionAgent("execution", bus)

    # =========================
    # REGISTER
    # =========================

    bus.subscribe(analyst)
    bus.subscribe(strategy)
    bus.subscribe(risk)
    bus.subscribe(execution)

    # =========================
    # WEBSOCKET
    # =========================

    ws = BinanceWS(bus)

    # =========================
    # START
    # =========================

    await ws.start()