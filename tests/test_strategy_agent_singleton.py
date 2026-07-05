# -*- coding: utf-8 -*-

"""
Regression test for core/agents/strategy_agent.py

Bug fixed: StrategyAgent instantiated its own SignalQualityService()
instead of using the shared signal_quality_service singleton that
AnalystAgent and ExecutionAgent use. Since cooldown tracking lives on
the service instance, this split state meant signal cooldowns
registered by ExecutionAgent were invisible to StrategyAgent's
cooldown checks (and vice versa for any service state mutated by
AnalystAgent), defeating the purpose of cooldown enforcement.
"""

from core.agents.strategy_agent import (
    StrategyAgent
)

from core.services.signal_quality_service import (
    signal_quality_service
)

from core.bus.event_bus import (
    EventBus
)


class TestStrategyAgentSharedSingleton:

    def test_uses_the_shared_signal_quality_service(self):

        bus = EventBus()

        agent = StrategyAgent(bus)

        assert agent.signal_quality is signal_quality_service

    def test_cooldown_registered_elsewhere_is_visible_to_strategy_agent(self):

        bus = EventBus()

        agent = StrategyAgent(bus)

        signal_quality_service.register_trade(
            user_id=42,
            symbol="BTCUSDT"
        )

        # if StrategyAgent had its own disconnected instance, this
        # cooldown registration would not be visible through it
        assert (
            agent.signal_quality
            is
            signal_quality_service
        )

        key = (
            signal_quality_service
            ._build_key(42, "BTCUSDT")
        )

        # the singleton's internal cooldown state must reflect the
        # registration, and agent.signal_quality must be the exact
        # same object holding that state
        assert key in signal_quality_service.signal_cooldowns

        assert key in agent.signal_quality.signal_cooldowns
