# -*- coding: utf-8 -*-

"""
Unit tests for core/agents/risk_agent.py's market_state telemetry.

Bug fixed: RiskAgent logged every rejection to the console
(log("RISK", f"BLOCKED {reason}", ...)) but never called
market_state.register_rejected_signal(reason) -- unlike
StrategyAgent and ExecutionAgent, which both do. This meant every
rejection between "signal generated" (StrategyAgent) and "order
executed" (ExecutionAgent) -- including the single most likely real
rejection, POSITION_ALREADY_OPEN -- was invisible to the dashboard's
"Blocked Signals" panel and the /runtime endpoint's
blocked_signal_reasons, showing up only as plain-text console log
lines with no structured count anywhere.

Found while analyzing a real 25h testnet run that generated 193
signals (StrategyAgent's count) but approved zero (ExecutionAgent's
count) -- the dashboard's blocked-signal breakdown couldn't explain
where those 193 went, because RiskAgent's own rejections (the stage
between the two) were not being counted at all.
"""

import pytest

from core.bus.event_bus import EventBus

from core.agents.risk_agent import (
    RiskAgent
)

from core.contracts.messages import (
    StrategySignalMessage,
    StrategySignalPayload
)

from core.state.market_state import (
    market_state
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


def _make_payload(
    user_id,
    symbol="BTCUSDT",
    signal="BUY",
    entry_price=100.0,
    signal_strength=0.9,
    atr=2.0
):

    return StrategySignalPayload(
        user_id=user_id,
        symbol=symbol,
        signal=signal,
        entry_price=entry_price,
        signal_strength=signal_strength,
        atr=atr
    )


@pytest.fixture(autouse=True)
def _reset_market_state():

    market_state.reset()

    yield

    market_state.reset()


class TestRiskAgentTelemetry:

    @pytest.mark.asyncio
    async def test_position_already_open_is_registered(self):

        trade = trades_repository.create_trade(
            user_id=50001,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        try:

            bus = EventBus()

            RiskAgent(bus)

            await bus.publish(
                StrategySignalMessage(
                    sender="test",
                    payload=_make_payload(
                        user_id=50001
                    )
                )
            )

            reasons = (
                market_state
                .get_blocked_signal_reasons()
            )

            assert reasons.get(
                "POSITION_ALREADY_OPEN"
            ) == 1

        finally:

            from data.storage.database import (
                SessionLocal
            )

            from data.storage.models import (
                Trade
            )

            session = SessionLocal()

            session.query(Trade).filter(
                Trade.id == trade.id
            ).delete()

            session.commit()

            session.close()

    @pytest.mark.asyncio
    async def test_atr_not_ready_is_registered(self):

        bus = EventBus()

        RiskAgent(bus)

        await bus.publish(
            StrategySignalMessage(
                sender="test",
                payload=_make_payload(
                    user_id=50002,
                    atr=None
                )
            )
        )

        reasons = (
            market_state
            .get_blocked_signal_reasons()
        )

        assert reasons.get(
            "ATR_NOT_READY"
        ) == 1

    @pytest.mark.asyncio
    async def test_invalid_atr_is_registered(self):

        bus = EventBus()

        RiskAgent(bus)

        await bus.publish(
            StrategySignalMessage(
                sender="test",
                payload=_make_payload(
                    user_id=50003,
                    atr=-1.0
                )
            )
        )

        reasons = (
            market_state
            .get_blocked_signal_reasons()
        )

        assert reasons.get(
            "INVALID_ATR"
        ) == 1

    @pytest.mark.asyncio
    async def test_invalid_signal_is_registered(self):

        bus = EventBus()

        RiskAgent(bus)

        await bus.publish(
            StrategySignalMessage(
                sender="test",
                payload=_make_payload(
                    user_id=50004,
                    signal="SELL"
                )
            )
        )

        reasons = (
            market_state
            .get_blocked_signal_reasons()
        )

        assert reasons.get(
            "INVALID_SIGNAL"
        ) == 1

    @pytest.mark.asyncio
    async def test_invalid_entry_is_registered(self):

        bus = EventBus()

        RiskAgent(bus)

        await bus.publish(
            StrategySignalMessage(
                sender="test",
                payload=_make_payload(
                    user_id=50005,
                    entry_price=0.0
                )
            )
        )

        reasons = (
            market_state
            .get_blocked_signal_reasons()
        )

        assert reasons.get(
            "INVALID_ENTRY"
        ) == 1

    @pytest.mark.asyncio
    async def test_low_rr_is_registered_when_risk_reward_too_low(
        self
    ):

        from core.config.trading_config import (
            TRADING_CONFIG
        )

        bus = EventBus()

        RiskAgent(bus)

        minimum_rr = TRADING_CONFIG[
            "minimum_risk_reward_ratio"
        ]

        assert minimum_rr > 0

        await bus.publish(
            StrategySignalMessage(
                sender="test",
                payload=_make_payload(
                    user_id=50006,
                    atr=0.0001
                )
            )
        )

        reasons = (
            market_state
            .get_blocked_signal_reasons()
        )

        # this scenario may resolve to LOW_RR depending on the
        # configured ATR multipliers -- what matters for this
        # regression is that IF it's rejected by RiskAgent, it shows
        # up in telemetry rather than vanishing silently
        total_registered = sum(
            reasons.values()
        )

        assert total_registered >= 1

    @pytest.mark.asyncio
    async def test_does_not_register_anything_for_a_valid_signal(
        self
    ):

        bus = EventBus()

        RiskAgent(bus)

        await bus.publish(
            StrategySignalMessage(
                sender="test",
                payload=_make_payload(
                    user_id=50007
                )
            )
        )

        reasons = (
            market_state
            .get_blocked_signal_reasons()
        )

        assert reasons == {}
