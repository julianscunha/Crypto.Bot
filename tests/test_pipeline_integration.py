# -*- coding: utf-8 -*-

"""
Integration tests exercising the full agent pipeline end to end:
RiskAgent -> ExecutionAgent -> PositionManagerAgent, using directly
constructed StrategySignalMessage payloads (bypassing AnalystAgent/
StrategyAgent so each test controls its inputs precisely).

These tests validate that, after all the bug fixes, a BUY signal can
flow all the way through to an opened trade in the database, and that
price updates correctly trigger stop-loss/take-profit/trailing-stop
exits via PositionManagerAgent.
"""

import pytest

from core.bus.event_bus import EventBus

from core.agents.risk_agent import RiskAgent
from core.agents.execution_agent import ExecutionAgent
from core.agents.position_manager_agent import PositionManagerAgent

from core.contracts.messages import (
    StrategySignalMessage,
    StrategySignalPayload,
    MarketDataMessage,
    MarketDataPayload
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


def _make_buy_signal(
    user_id=500,
    symbol="BTCUSDT",
    entry_price=100.0,
    atr=2.0
):

    payload = StrategySignalPayload(
        user_id=user_id,
        symbol=symbol,
        signal="BUY",
        entry_price=entry_price,
        atr=atr
    )

    return StrategySignalMessage(
        sender="test",
        payload=payload
    )


class TestFullEntryPipeline:

    @pytest.mark.asyncio
    async def test_buy_signal_results_in_open_trade(self):

        bus = EventBus()

        RiskAgent(bus)
        ExecutionAgent(bus)
        PositionManagerAgent(bus)

        signal = _make_buy_signal(
            user_id=500,
            symbol="BTCUSDT",
            entry_price=100.0,
            atr=2.0
        )

        await bus.publish(signal)

        open_trades = trades_repository.get_open_trades(
            user_id=500
        )

        assert len(open_trades) == 1

        trade = open_trades[0]

        assert trade.symbol == "BTCUSDT"

        assert trade.action == "BUY"

        assert trade.status == "OPEN"

    @pytest.mark.asyncio
    async def test_no_atr_blocks_entry(self):

        bus = EventBus()

        RiskAgent(bus)
        ExecutionAgent(bus)
        PositionManagerAgent(bus)

        signal = _make_buy_signal(
            user_id=501,
            atr=None
        )

        await bus.publish(signal)

        open_trades = trades_repository.get_open_trades(
            user_id=501
        )

        assert len(open_trades) == 0

    @pytest.mark.asyncio
    async def test_duplicate_signal_does_not_open_second_position(self):

        bus = EventBus()

        RiskAgent(bus)
        ExecutionAgent(bus)
        PositionManagerAgent(bus)

        signal = _make_buy_signal(user_id=502)

        await bus.publish(signal)

        await bus.publish(signal)

        open_trades = trades_repository.get_open_trades(
            user_id=502
        )

        assert len(open_trades) == 1

    @pytest.mark.asyncio
    async def test_telemetry_shows_zero_delivery_failures(self):

        bus = EventBus()

        RiskAgent(bus)
        ExecutionAgent(bus)
        PositionManagerAgent(bus)

        signal = _make_buy_signal(user_id=503)

        await bus.publish(signal)

        telemetry = bus.get_telemetry()

        assert telemetry["total_failed_deliveries"] == 0


class TestPositionManagementExits:

    @pytest.mark.asyncio
    async def test_price_drop_triggers_stop_loss_exit(self):

        bus = EventBus()

        RiskAgent(bus)
        ExecutionAgent(bus)
        PositionManagerAgent(bus)

        signal = _make_buy_signal(
            user_id=510,
            symbol="BTCUSDT",
            entry_price=100.0,
            atr=2.0
        )

        await bus.publish(signal)

        open_trades = trades_repository.get_open_trades(
            user_id=510
        )

        assert len(open_trades) == 1

        trade = open_trades[0]

        stop_loss = trade.stop_loss

        # drive price down through the stop-loss level
        price_drop_payload = MarketDataPayload(
            user_id=510,
            symbol="BTCUSDT",
            open=stop_loss,
            high=stop_loss,
            low=stop_loss - 1.0,
            close=stop_loss - 0.5,
            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=price_drop_payload
            )
        )

        closed_trades = trades_repository.get_closed_trades(
            user_id=510
        )

        assert len(closed_trades) == 1

        assert closed_trades[0].exit_reason == "STOP_LOSS"

        assert trades_repository.has_open_trade(
            user_id=510,
            symbol="BTCUSDT"
        ) is False

    @pytest.mark.asyncio
    async def test_price_rise_triggers_take_profit_exit(self):

        bus = EventBus()

        RiskAgent(bus)
        ExecutionAgent(bus)
        PositionManagerAgent(bus)

        signal = _make_buy_signal(
            user_id=511,
            symbol="BTCUSDT",
            entry_price=100.0,
            atr=2.0
        )

        await bus.publish(signal)

        trade = trades_repository.get_open_trades(
            user_id=511
        )[0]

        take_profit = trade.take_profit

        price_rise_payload = MarketDataPayload(
            user_id=511,
            symbol="BTCUSDT",
            open=take_profit,
            high=take_profit + 1.0,
            low=take_profit,
            close=take_profit + 0.5,
            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=price_rise_payload
            )
        )

        closed_trades = trades_repository.get_closed_trades(
            user_id=511
        )

        assert len(closed_trades) == 1

        assert closed_trades[0].exit_reason == "TAKE_PROFIT"
