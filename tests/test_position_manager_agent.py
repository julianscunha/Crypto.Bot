# -*- coding: utf-8 -*-

"""
Unit tests for core/agents/position_manager_agent.py

Covers stop loss / take profit / trailing stop exits (previously
untested) and the breakeven feature implemented in this session.

== Breakeven bug history ==

enable_breakeven and breakeven_trigger_percent existed in
core/config/trade_management_config.py, and a breakeven_enabled
column existed on every Trade row, since early in this project --
but no code anywhere ever read either. The feature was fully wired
up in config/schema but never implemented.

Implementing it surfaced two further bugs:

1. ExecutionAgent hardcoded breakeven_enabled=True on every created
   trade (and TradesRepository.create_trade defaulted to True too).
   Reusing this column to mean "breakeven has already been applied
   to this trade" (its only sensible reading, since it was never
   used to mean "is enabled for this trade" -- that's what
   TRADE_MANAGEMENT_CONFIG["enable_breakeven"] is for) meant every
   new trade looked like it had ALREADY had breakeven applied,
   permanently blocking it from ever triggering.

2. PositionManagerAgent._apply_breakeven originally set
   `trade.breakeven_enabled = True` directly on the in-memory Trade
   object after calling update_stop_loss() -- but
   TradesRepository methods each open their own session
   (session.merge() on a fresh session), so mutating the caller's
   own object doesn't persist anything. The flag update only ever
   reached the database via update_stop_loss()'s own
   mark_breakeven_applied parameter, set atomically in the same
   transaction as the stop_loss move.
"""

import pytest

from unittest.mock import patch

from core.bus.event_bus import EventBus

from core.agents.position_manager_agent import (
    PositionManagerAgent
)

from core.contracts.messages import (
    MarketDataMessage,
    MarketDataPayload
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.services.binance_trading_client import (
    BinanceTradingClient,
    BinanceTradingError
)


def _open_trade(
    user_id,
    entry_price=100.0,
    stop_loss=95.0,
    take_profit=110.0,
    trailing_stop=1.0,
    entry_order_id=None,
    order_list_id=None
):

    return trades_repository.create_trade(
        user_id=user_id,
        symbol="BTCUSDT",
        action="BUY",
        entry_price=entry_price,
        quantity=1.0,
        stop_loss=stop_loss,
        take_profit=take_profit,
        trailing_stop=trailing_stop,
        entry_order_id=entry_order_id,
        order_list_id=order_list_id
    )


class TestCreateTradeBreakevenDefault:

    def test_new_trades_start_with_breakeven_not_yet_applied(self):

        # regression: this previously defaulted to True, which
        # permanently blocked breakeven from ever triggering on any
        # trade, since _apply_breakeven treats True as "already done"
        trade = _open_trade(user_id=40001)

        assert trade.breakeven_enabled is False


class TestApplyBreakeven:

    @pytest.mark.asyncio
    async def test_does_not_trigger_below_profit_threshold(self):

        trade = _open_trade(user_id=40002)

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        # well below the trigger
        below_trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent / 2) / 100)
        )

        await agent._apply_breakeven(
            trade,
            below_trigger_price
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == trade.stop_loss

        assert fresh.breakeven_enabled is False

    @pytest.mark.asyncio
    async def test_triggers_at_profit_threshold(self):

        trade = _open_trade(user_id=40003)

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        await agent._apply_breakeven(
            trade,
            trigger_price
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == trade.entry_price

        assert fresh.breakeven_enabled is True

    @pytest.mark.asyncio
    async def test_only_applies_once_per_trade(self):

        trade = _open_trade(user_id=40004)

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        first_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        await agent._apply_breakeven(
            trade,
            first_price
        )

        # price keeps rising well past the original trigger --
        # breakeven must not move the stop again
        much_higher_price = (
            trade.entry_price
            *
            1.10
        )

        await agent._apply_breakeven(
            trade,
            much_higher_price
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == trade.entry_price

    @pytest.mark.asyncio
    async def test_disabled_filter_never_triggers(self):

        trade = _open_trade(user_id=40005)

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_breakeven"
        ]

        try:

            agent.config[
                "enable_breakeven"
            ] = False

            await agent._apply_breakeven(
                trade,
                trade.entry_price * 1.10
            )

            fresh = trades_repository.get_trade(
                trade.id
            )

            assert fresh.stop_loss == 95.0

            assert fresh.breakeven_enabled is False

        finally:

            agent.config[
                "enable_breakeven"
            ] = original

    @pytest.mark.asyncio
    async def test_never_moves_stop_loss_backward(self):

        # if stop_loss is already at or above entry_price (e.g. a
        # prior trailing-stop adjustment), breakeven must never move
        # it backward toward/below entry
        trade = _open_trade(
            user_id=40006,
            entry_price=100.0,
            stop_loss=102.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        await agent._apply_breakeven(
            trade,
            105.0
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == 102.0


class TestPositionManagerPipelineIntegration:

    @pytest.mark.asyncio
    async def test_breakeven_triggers_through_real_market_data_message(
        self
    ):

        trade = _open_trade(user_id=40007)

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        payload = MarketDataPayload(

            user_id=40007,

            symbol="BTCUSDT",

            open=trigger_price,

            high=trigger_price,

            low=trigger_price,

            close=trigger_price,

            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=payload
            )
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == trade.entry_price

    @pytest.mark.asyncio
    async def test_stop_loss_exit_closes_position(self):

        trade = _open_trade(
            user_id=40008,
            entry_price=100.0,
            stop_loss=95.0
        )

        bus = EventBus()

        PositionManagerAgent(bus)

        payload = MarketDataPayload(

            user_id=40008,

            symbol="BTCUSDT",

            open=94.0,

            high=94.0,

            low=94.0,

            close=94.0,

            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=payload
            )
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "STOP_LOSS"

    @pytest.mark.asyncio
    async def test_take_profit_exit_closes_position(self):

        trade = _open_trade(
            user_id=40009,
            entry_price=100.0,
            take_profit=110.0
        )

        bus = EventBus()

        PositionManagerAgent(bus)

        payload = MarketDataPayload(

            user_id=40009,

            symbol="BTCUSDT",

            open=111.0,

            high=111.0,

            low=111.0,

            close=111.0,

            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=payload
            )
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "TAKE_PROFIT"

    @pytest.mark.asyncio
    async def test_ignores_market_data_for_a_different_symbol(self):

        trade = _open_trade(user_id=40010)

        bus = EventBus()

        PositionManagerAgent(bus)

        payload = MarketDataPayload(

            user_id=40010,

            symbol="ETHUSDT",

            open=1.0,

            high=1.0,

            low=1.0,

            close=1.0,

            volume=10.0
        )

        await bus.publish(
            MarketDataMessage(
                sender="test",
                payload=payload
            )
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "OPEN"


class TestAtrTrailingStop:

    """
    Bug fixed: enable_atr_trailing existed in
    core/config/trade_management_config.py since early in this
    project, but no code anywhere ever read it. The trailing
    distance was always trade.trailing_stop -- a value computed
    once from the ATR available at entry time (RiskAgent's
    atr * atr_trailing_multiplier) and then frozen for the entire
    life of the position, never adapting if volatility changed
    afterward.

    Disabled by default (matches the project's existing default and
    the user's .env, which never set this) -- enabling it is opt-in
    and changes zero behavior until a person deliberately turns it
    on.
    """

    def test_disabled_by_default_uses_frozen_distance(self):

        trade = _open_trade(
            user_id=40011
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        assert agent.config[
            "enable_atr_trailing"
        ] is False

        distance = agent._resolve_trailing_distance(
            trade
        )

        assert distance == trade.trailing_stop

    def test_enabled_falls_back_to_frozen_distance_when_atr_unavailable(
        self
    ):

        trade = _open_trade(
            user_id=40012
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_atr_trailing"
        ]

        try:

            agent.config[
                "enable_atr_trailing"
            ] = True

            # no candles have been fed into atr_service for this
            # user/symbol -- calculate_atr() returns None (warmup)
            distance = agent._resolve_trailing_distance(
                trade
            )

            assert distance == trade.trailing_stop

        finally:

            agent.config[
                "enable_atr_trailing"
            ] = original

    def test_enabled_uses_current_atr_when_available(self):

        trade = _open_trade(
            user_id=40013
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_atr_trailing"
        ]

        try:

            agent.config[
                "enable_atr_trailing"
            ] = True

            with patch.object(
                agent.atr_service,
                "calculate_atr",
                return_value=2.5
            ):

                distance = agent._resolve_trailing_distance(
                    trade
                )

            multiplier = agent.config[
                "atr_trailing_multiplier"
            ]

            assert distance == 2.5 * multiplier

            assert distance != trade.trailing_stop

        finally:

            agent.config[
                "enable_atr_trailing"
            ] = original

    @pytest.mark.asyncio
    async def test_dynamic_distance_flows_through_real_pipeline(
        self
    ):

        # exercises the real ordering dependency: AnalystAgent must
        # process each MarketDataMessage (feeding atr_service's
        # candle cache) before PositionManagerAgent reads the
        # current ATR for the same message -- EventBus.publish()
        # awaits each subscriber in registration order, so
        # registering AnalystAgent first is what makes this safe
        import random

        from core.agents.analyst_agent import AnalystAgent

        trade = _open_trade(
            user_id=40014,
            take_profit=200.0
        )

        bus = EventBus()

        AnalystAgent(bus)

        agent = PositionManagerAgent(bus)

        agent.config[
            "enable_atr_trailing"
        ] = True

        random.seed(7)

        price = 100.0

        for _ in range(25):

            price += random.uniform(-0.5, 1.0)

            payload = MarketDataPayload(

                user_id=40014,

                symbol="BTCUSDT",

                open=price,

                high=price + 0.5,

                low=price - 0.5,

                close=price,

                volume=10.0
            )

            await bus.publish(
                MarketDataMessage(
                    sender="test",
                    payload=payload
                )
            )

        current_atr = agent.atr_service.calculate_atr(
            user_id=40014,

            symbol="BTCUSDT"
        )

        assert current_atr is not None

        fresh = trades_repository.get_trade(
            trade.id
        )

        distance = agent._resolve_trailing_distance(
            fresh
        )

        multiplier = agent.config[
            "atr_trailing_multiplier"
        ]

        assert distance == round(
            current_atr * multiplier,
            10
        )


class TestDynamicTakeProfit:

    """
    Bug fixed: enable_dynamic_take_profit existed in
    core/config/trade_management_config.py since early in this
    project, but no code anywhere ever read it. take_profit was
    always fixed at whatever RiskAgent calculated at entry time, for
    the entire life of the position -- a winning trade always closed
    at the original target even if the market kept moving favorably.

    Disabled by default -- enabling it is opt-in and changes zero
    behavior until a person deliberately turns it on.

    Extension requires BOTH the price-proximity gate (default 90% of
    the entry-to-target distance) AND a BULLISH market regime (this
    codebase is long-only) -- either condition failing must block
    the extension.
    """

    @pytest.mark.asyncio
    async def test_disabled_by_default_never_extends(self):

        trade = _open_trade(
            user_id=40015,
            take_profit=110.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        assert agent.config[
            "enable_dynamic_take_profit"
        ] is False

        await agent._apply_dynamic_take_profit(
            trade,
            109.5
        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.take_profit == 110.0

        assert fresh.take_profit_extended is False

    @pytest.mark.asyncio
    async def test_enabled_but_price_not_close_enough_does_not_extend(
        self
    ):

        trade = _open_trade(
            user_id=40016,
            take_profit=110.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_dynamic_take_profit"
        ]

        try:

            agent.config[
                "enable_dynamic_take_profit"
            ] = True

            # only 50% of the way from entry (100) to target (110)
            await agent._apply_dynamic_take_profit(
                trade,
                105.0
            )

            fresh = trades_repository.get_trade(
                trade.id
            )

            assert fresh.take_profit == 110.0

        finally:

            agent.config[
                "enable_dynamic_take_profit"
            ] = original

    @pytest.mark.asyncio
    async def test_close_to_target_but_non_bullish_regime_does_not_extend(
        self
    ):

        trade = _open_trade(
            user_id=40017,
            take_profit=110.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_dynamic_take_profit"
        ]

        try:

            agent.config[
                "enable_dynamic_take_profit"
            ] = True

            with patch.object(
                agent.market_regime,
                "detect_regime",
                return_value="SIDEWAYS"
            ):

                # 95% of the way there -- proximity gate passes,
                # regime gate must block it
                await agent._apply_dynamic_take_profit(
                    trade,
                    109.5
                )

            fresh = trades_repository.get_trade(
                trade.id
            )

            assert fresh.take_profit == 110.0

        finally:

            agent.config[
                "enable_dynamic_take_profit"
            ] = original

    @pytest.mark.asyncio
    async def test_extends_when_both_gates_pass(self):

        trade = _open_trade(
            user_id=40018,
            take_profit=110.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_dynamic_take_profit"
        ]

        try:

            agent.config[
                "enable_dynamic_take_profit"
            ] = True

            with patch.object(
                agent.market_regime,
                "detect_regime",
                return_value="BULLISH"
            ):

                with patch.object(
                    agent.atr_service,
                    "calculate_atr",
                    return_value=2.0
                ):

                    await agent._apply_dynamic_take_profit(
                        trade,
                        109.5
                    )

            fresh = trades_repository.get_trade(
                trade.id
            )

            multiplier = agent.config[
                "dynamic_take_profit_atr_multiplier"
            ]

            assert fresh.take_profit == (
                110.0
                +
                (2.0 * multiplier)
            )

            assert fresh.take_profit_extended is True

        finally:

            agent.config[
                "enable_dynamic_take_profit"
            ] = original

    @pytest.mark.asyncio
    async def test_only_extends_once_per_trade(self):

        trade = _open_trade(
            user_id=40019,
            take_profit=110.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_dynamic_take_profit"
        ]

        try:

            agent.config[
                "enable_dynamic_take_profit"
            ] = True

            with patch.object(
                agent.market_regime,
                "detect_regime",
                return_value="BULLISH"
            ):

                with patch.object(
                    agent.atr_service,
                    "calculate_atr",
                    return_value=2.0
                ):

                    await agent._apply_dynamic_take_profit(
                        trade,
                        109.5
                    )

                    first_extension = (
                        trades_repository
                        .get_trade(trade.id)
                        .take_profit
                    )

                    # price keeps climbing, still meets every gate --
                    # must NOT extend a second time
                    await agent._apply_dynamic_take_profit(
                        trade,
                        first_extension - 0.1
                    )

            fresh = trades_repository.get_trade(
                trade.id
            )

            assert fresh.take_profit == first_extension

        finally:

            agent.config[
                "enable_dynamic_take_profit"
            ] = original

    @pytest.mark.asyncio
    async def test_does_not_crash_on_inverted_target(self):

        # defensive: take_profit <= entry_price would make the
        # proximity calculation meaningless (division producing a
        # nonsensical or negative percentage) -- must return safely
        trade = _open_trade(
            user_id=40020,
            entry_price=100.0,
            take_profit=90.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        original = agent.config[
            "enable_dynamic_take_profit"
        ]

        try:

            agent.config[
                "enable_dynamic_take_profit"
            ] = True

            await agent._apply_dynamic_take_profit(
                trade,
                95.0
            )

            fresh = trades_repository.get_trade(
                trade.id
            )

            assert fresh.take_profit == 90.0

        finally:

            agent.config[
                "enable_dynamic_take_profit"
            ] = original

    @pytest.mark.asyncio
    async def test_extension_flows_through_real_pipeline_with_real_regime_detection(
        self
    ):

        from core.agents.analyst_agent import AnalystAgent

        trade = _open_trade(
            user_id=40021,
            entry_price=100.0,
            take_profit=110.0
        )

        bus = EventBus()

        AnalystAgent(bus)

        agent = PositionManagerAgent(bus)

        agent.config[
            "enable_dynamic_take_profit"
        ] = True

        price = 100.0

        for _ in range(20):

            price += 0.5

            payload = MarketDataPayload(

                user_id=40021,

                symbol="BTCUSDT",

                open=price,

                high=price + 0.2,

                low=price - 0.2,

                close=price,

                volume=10.0
            )

            await bus.publish(
                MarketDataMessage(
                    sender="test",
                    payload=payload
                )
            )

        fresh = trades_repository.get_trade(
            trade.id
        )

        # the position must still be OPEN (not closed at the
        # original 110.0 target) and the target itself extended
        # past 110.0
        assert fresh.status == "OPEN"

        assert fresh.take_profit > 110.0

        assert fresh.take_profit_extended is True


class TestLiveExitTouchesRealExchange:

    """
    Bug fixed: _close_position previously only ever updated the
    local trades row, for BOTH paper and live. A LIVE TRAILING_STOP
    exit (no resting order on Binance covers this at all) never
    actually closed the real position -- it stayed open and
    unprotected on the exchange while the local database showed it
    as closed. Even a STOP_LOSS/TAKE_PROFIT exit (which the OCO
    *should* cover) was marked closed locally without ever
    confirming the OCO actually filled on the exchange's side.

    All Binance calls are mocked (this sandbox has no network
    access to Binance). PAPER trades (order_list_id=None) are
    covered by the rest of this file and are deliberately not
    touched by any of these tests -- _get_live_client() and the
    order_list_id check together are what keep PAPER untouched.

    breakeven and dynamic_take_profit are disabled for every test
    in this class: both can legitimately fire on the same candle as
    a STOP_LOSS/TAKE_PROFIT/TRAILING_STOP exit (e.g. a price that
    crosses both the breakeven trigger and the trailing stop level
    at once), which is correct real behavior but would make these
    exit-focused tests exercise two features' interaction instead
    of the one each is meant to isolate. That interaction is its
    own thing, covered separately where it's the point of the test.
    """

    @pytest.fixture(autouse=True)
    def _disable_breakeven_and_dynamic_take_profit(self):

        from core.config.trade_management_config import (
            TRADE_MANAGEMENT_CONFIG
        )

        original_breakeven = TRADE_MANAGEMENT_CONFIG[
            "enable_breakeven"
        ]

        original_dynamic_tp = TRADE_MANAGEMENT_CONFIG[
            "enable_dynamic_take_profit"
        ]

        TRADE_MANAGEMENT_CONFIG["enable_breakeven"] = False

        TRADE_MANAGEMENT_CONFIG["enable_dynamic_take_profit"] = (
            False
        )

        yield

        TRADE_MANAGEMENT_CONFIG["enable_breakeven"] = (
            original_breakeven
        )

        TRADE_MANAGEMENT_CONFIG["enable_dynamic_take_profit"] = (
            original_dynamic_tp
        )

    @staticmethod
    def _live_trade(user_id):

        return _open_trade(
            user_id=user_id,
            entry_order_id="555111",
            order_list_id="777222"
        )

    @pytest.mark.asyncio
    async def test_stop_loss_closes_locally_once_oco_confirms_all_done(
        self
    ):

        trade = self._live_trade(
            user_id=50001
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_status(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "get_order_list_status",
                new=fake_status
            ):

                await agent._process_position(
                    trade=trade,
                    market_price=94.0
                )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "STOP_LOSS"

    @pytest.mark.asyncio
    async def test_stop_loss_stays_open_locally_while_oco_still_executing(
        self
    ):

        # the local price feed crossed stop_loss this candle, but
        # Binance's own order book hasn't matched the leg yet --
        # must NOT mark closed ahead of the real exchange state
        trade = self._live_trade(
            user_id=50002
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_status(self, symbol, order_list_id):

            return {"listOrderStatus": "EXECUTING"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "get_order_list_status",
                new=fake_status
            ):

                await agent._process_position(
                    trade=trade,
                    market_price=94.0
                )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "OPEN"

    @pytest.mark.asyncio
    async def test_stop_loss_stays_open_locally_when_status_check_fails(
        self
    ):

        trade = self._live_trade(
            user_id=50003
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_status(self, symbol, order_list_id):

            raise BinanceTradingError(
                "simulated network error"
            )

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "get_order_list_status",
                new=fake_status
            ):

                await agent._process_position(
                    trade=trade,
                    market_price=94.0
                )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "OPEN"

    @pytest.mark.asyncio
    async def test_take_profit_closes_locally_once_oco_confirms_all_done(
        self
    ):

        trade = self._live_trade(
            user_id=50004
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_status(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "get_order_list_status",
                new=fake_status
            ):

                await agent._process_position(
                    trade=trade,
                    market_price=111.0
                )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "TAKE_PROFIT"

    @pytest.mark.asyncio
    async def test_trailing_stop_cancels_oco_and_sells_at_market(
        self
    ):

        trade = self._live_trade(
            user_id=50005
        )

        # force highest_price/trailing distance so trailing_stop_price
        # is hit by a price drop from a prior high
        trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=120.0,
            unrealized_pnl=20.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        cancel_calls = []

        sell_calls = []

        async def fake_cancel(self, symbol, order_list_id):

            cancel_calls.append(
                (symbol, order_list_id)
            )

            return {"listOrderStatus": "ALL_DONE"}

        async def fake_market_order(
            self, symbol, side, quantity, client_order_id=None
        ):

            sell_calls.append(
                (symbol, side, quantity)
            )

            return {
                "executedQty": str(quantity),
                "cummulativeQuoteQty": str(quantity * 115.0)
            }

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order
                ):

                    # price well below the trailing stop level
                    await agent._process_position(
                        trade=trade,
                        market_price=100.5
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "TRAILING_STOP"

        assert len(cancel_calls) == 1

        assert len(sell_calls) == 1

        assert sell_calls[0] == (
            "BTCUSDT", "SELL", trade.quantity
        )

    @pytest.mark.asyncio
    async def test_trailing_stop_stays_open_when_market_sell_fails(
        self
    ):

        # OCO cancel succeeds, but the emergency market sell fails
        # -- the worst real-money state this code can produce
        # (unprotected position). Must not mark closed locally,
        # since that would hide a real, unprotected position behind
        # a database lie.
        trade = self._live_trade(
            user_id=50006
        )

        trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=120.0,
            unrealized_pnl=20.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_cancel(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        async def fake_market_order_fails(
            self, symbol, side, quantity, client_order_id=None
        ):

            raise BinanceTradingError(
                "simulated exchange rejection"
            )

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fake_market_order_fails
                ):

                    await agent._process_position(
                        trade=trade,
                        market_price=100.5
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "OPEN"

    @pytest.mark.asyncio
    async def test_trailing_stop_race_oco_already_filled_closes_locally(
        self
    ):

        # cancel_order_list fails because the OCO already executed
        # on Binance's side between this agent's last price check
        # and now (a real race between two independent triggers) --
        # the position IS closed for real, just not via this path.
        # Must close locally too, not retry forever.
        trade = self._live_trade(
            user_id=50007
        )

        trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=120.0,
            unrealized_pnl=20.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_cancel_fails(self, symbol, order_list_id):

            raise BinanceTradingError(
                "Unknown order sent (already filled/canceled)"
            )

        async def fake_status_all_done(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel_fails
            ):

                with patch.object(
                    BinanceTradingClient,
                    "get_order_list_status",
                    new=fake_status_all_done
                ):

                    await agent._process_position(
                        trade=trade,
                        market_price=100.5
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "TRAILING_STOP"

    @pytest.mark.asyncio
    async def test_trailing_stop_stays_open_when_cancel_fails_and_oco_not_resolved(
        self
    ):

        # cancel fails for a genuine reason unrelated to a race
        # (e.g. transient network error) -- the OCO is still
        # EXECUTING, so this must retry next candle, not assume a
        # race and close locally
        trade = self._live_trade(
            user_id=50008
        )

        trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=120.0,
            unrealized_pnl=20.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fake_cancel_fails(self, symbol, order_list_id):

            raise BinanceTradingError(
                "simulated transient network error"
            )

        async def fake_status_still_executing(
            self, symbol, order_list_id
        ):

            return {"listOrderStatus": "EXECUTING"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel_fails
            ):

                with patch.object(
                    BinanceTradingClient,
                    "get_order_list_status",
                    new=fake_status_still_executing
                ):

                    await agent._process_position(
                        trade=trade,
                        market_price=100.5
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "OPEN"

    @pytest.mark.asyncio
    async def test_paper_trade_never_calls_binance_at_all(
        self
    ):

        # order_list_id=None (PAPER) -- _close_position must take
        # the original, unmodified local-only path. Patching the
        # client methods to raise guarantees the test fails loudly
        # if PAPER ever accidentally reaches them.
        trade = _open_trade(
            user_id=50009
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        async def fail_if_called(*args, **kwargs):

            raise AssertionError(
                "PAPER trade must never call the live Binance client"
            )

        with patch.object(
            BinanceTradingClient,
            "get_order_list_status",
            new=fail_if_called
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fail_if_called
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_market_order",
                    new=fail_if_called
                ):

                    await agent._process_position(
                        trade=trade,
                        market_price=94.0
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "STOP_LOSS"


class TestLiveBreakevenReplacesOco:

    """
    Bug fixed: _apply_breakeven previously moved stop_loss in the
    local row only. For a LIVE trade, the real protective stop only
    exists inside the OCO already resting on Binance, and a resting
    order's leg can't be edited in place -- the only way to
    actually move it is cancel the existing OCO and place a new one
    with the new stop_loss (same take_profit). Without that, the
    local database would claim the position was moved to breakeven
    while the real exchange-side stop never moved at all.
    """

    @staticmethod
    def _live_trade(user_id, entry_price=100.0, stop_loss=95.0):

        return _open_trade(
            user_id=user_id,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=110.0,
            entry_order_id="555111",
            order_list_id="777222"
        )

    @pytest.mark.asyncio
    async def test_cancels_old_oco_and_places_new_one_with_moved_stop(
        self
    ):

        trade = self._live_trade(
            user_id=60001
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        cancel_calls = []

        oco_calls = []

        async def fake_cancel(self, symbol, order_list_id):

            cancel_calls.append(
                (symbol, order_list_id)
            )

            return {"listOrderStatus": "ALL_DONE"}

        async def fake_oco(self, **kwargs):

            oco_calls.append(kwargs)

            return {"orderListId": 999888}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_oco_sell_order",
                    new=fake_oco
                ):

                    await agent._apply_breakeven(
                        trade,
                        trigger_price
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == trade.entry_price

        assert fresh.breakeven_enabled is True

        assert fresh.order_list_id == "999888"

        assert cancel_calls == [
            ("BTCUSDT", 777222)
        ]

        assert len(oco_calls) == 1

        # take_profit must stay exactly where it was -- breakeven
        # only ever moves the stop_loss leg
        assert float(oco_calls[0]["take_profit_price"]) == 110.0

        assert float(oco_calls[0]["stop_loss_price"]) == trade.entry_price

    @pytest.mark.asyncio
    async def test_does_not_apply_locally_when_oco_cancel_fails(
        self
    ):

        trade = self._live_trade(
            user_id=60002
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        async def fake_cancel_fails(self, symbol, order_list_id):

            raise BinanceTradingError(
                "simulated transient network error"
            )

        async def fake_status_still_executing(
            self, symbol, order_list_id
        ):

            return {"listOrderStatus": "EXECUTING"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel_fails
            ):

                with patch.object(
                    BinanceTradingClient,
                    "get_order_list_status",
                    new=fake_status_still_executing
                ):

                    await agent._apply_breakeven(
                        trade,
                        trigger_price
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        # the real stop never moved -- the local record must not
        # claim breakeven was applied
        assert fresh.stop_loss == 95.0

        assert fresh.breakeven_enabled is False

        assert fresh.order_list_id == "777222"

    @pytest.mark.asyncio
    async def test_falls_back_to_emergency_close_when_new_oco_fails(
        self
    ):

        # the old OCO is canceled successfully, but the replacement
        # fails to place -- the position is now genuinely
        # unprotected (no resting order at all), so this must close
        # it immediately at market rather than leave it exposed
        trade = self._live_trade(
            user_id=60003
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        sell_calls = []

        async def fake_cancel(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        async def fake_oco_fails(self, **kwargs):

            raise BinanceTradingError(
                "simulated exchange rejection"
            )

        async def fake_market_sell(
            self, symbol, side, quantity, client_order_id=None
        ):

            sell_calls.append(
                (symbol, side, quantity)
            )

            return {
                "executedQty": str(quantity),
                "cummulativeQuoteQty": str(quantity * trigger_price)
            }

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel
            ):

                with patch.object(
                    BinanceTradingClient,
                    "place_oco_sell_order",
                    new=fake_oco_fails
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_market_order",
                        new=fake_market_sell
                    ):

                        await agent._apply_breakeven(
                            trade,
                            trigger_price
                        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert fresh.exit_reason == "BREAKEVEN_EMERGENCY_CLOSE"

        assert len(sell_calls) == 1

    @pytest.mark.asyncio
    async def test_skips_replacement_when_oco_already_resolved(
        self
    ):

        # the position already hit TP/SL for real between this
        # agent's last check and now -- nothing left to move
        trade = self._live_trade(
            user_id=60004
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        async def fake_cancel_fails(self, symbol, order_list_id):

            raise BinanceTradingError(
                "Unknown order sent (already filled/canceled)"
            )

        async def fake_status_all_done(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fake_cancel_fails
            ):

                with patch.object(
                    BinanceTradingClient,
                    "get_order_list_status",
                    new=fake_status_all_done
                ):

                    await agent._apply_breakeven(
                        trade,
                        trigger_price
                    )

        fresh = trades_repository.get_trade(
            trade.id
        )

        # breakeven must not claim it was applied -- the position
        # is no longer open at all
        assert fresh.breakeven_enabled is False

        assert fresh.order_list_id == "777222"

    @pytest.mark.asyncio
    async def test_paper_trade_breakeven_never_calls_binance(
        self
    ):

        trade = _open_trade(
            user_id=60005
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        trigger_percent = agent.config[
            "breakeven_trigger_percent"
        ]

        trigger_price = (
            trade.entry_price
            *
            (1 + (trigger_percent + 0.1) / 100)
        )

        async def fail_if_called(*args, **kwargs):

            raise AssertionError(
                "PAPER trade must never call the live Binance client"
            )

        with patch.object(
            BinanceTradingClient,
            "cancel_order_list",
            new=fail_if_called
        ):

            await agent._apply_breakeven(
                trade,
                trigger_price
            )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.stop_loss == trade.entry_price

        assert fresh.breakeven_enabled is True


class TestLiveDynamicTakeProfitReplacesOco:

    """
    Bug fixed: _apply_dynamic_take_profit previously extended
    take_profit in the local row only. For a LIVE trade, the real
    target only exists inside the OCO already resting on Binance,
    and a resting order's leg can't be edited in place -- the only
    way to actually move it is cancel the existing OCO and place a
    new one with the extended take_profit (same stop_loss). Mirrors
    TestLiveBreakevenReplacesOco's scenarios exactly, since both
    features share the same _replace_oco implementation.
    """

    @staticmethod
    def _live_trade_near_target(user_id):

        trade = _open_trade(
            user_id=user_id,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            entry_order_id="555111",
            order_list_id="777222"
        )

        return trade

    @staticmethod
    def _enable_and_mock_gates(agent):

        agent.config[
            "enable_dynamic_take_profit"
        ] = True

        return (

            patch.object(
                agent.market_regime,
                "detect_regime",
                return_value="BULLISH"
            ),

            patch.object(
                agent.atr_service,
                "calculate_atr",
                return_value=2.0
            )
        )

    @pytest.mark.asyncio
    async def test_cancels_old_oco_and_places_new_one_with_extended_target(
        self
    ):

        trade = self._live_trade_near_target(
            user_id=60101
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        regime_patch, atr_patch = (
            self._enable_and_mock_gates(agent)
        )

        cancel_calls = []

        oco_calls = []

        async def fake_cancel(self, symbol, order_list_id):

            cancel_calls.append(
                (symbol, order_list_id)
            )

            return {"listOrderStatus": "ALL_DONE"}

        async def fake_oco(self, **kwargs):

            oco_calls.append(kwargs)

            return {"orderListId": 999777}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with regime_patch, atr_patch:

                with patch.object(
                    BinanceTradingClient,
                    "cancel_order_list",
                    new=fake_cancel
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco
                    ):

                        # close enough to target to clear the
                        # proximity gate
                        await agent._apply_dynamic_take_profit(
                            trade,
                            109.5
                        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        multiplier = agent.config[
            "dynamic_take_profit_atr_multiplier"
        ]

        expected_take_profit = (
            110.0
            +
            (2.0 * multiplier)
        )

        assert fresh.take_profit == expected_take_profit

        assert fresh.take_profit_extended is True

        assert fresh.order_list_id == "999777"

        assert cancel_calls == [
            ("BTCUSDT", 777222)
        ]

        assert len(oco_calls) == 1

        # stop_loss must stay exactly where it was -- dynamic take
        # profit only ever moves the take_profit leg
        assert float(oco_calls[0]["stop_loss_price"]) == 95.0

        assert (
            float(oco_calls[0]["take_profit_price"])
            ==
            expected_take_profit
        )

    @pytest.mark.asyncio
    async def test_does_not_apply_locally_when_oco_cancel_fails(
        self
    ):

        trade = self._live_trade_near_target(
            user_id=60102
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        regime_patch, atr_patch = (
            self._enable_and_mock_gates(agent)
        )

        async def fake_cancel_fails(self, symbol, order_list_id):

            raise BinanceTradingError(
                "simulated transient network error"
            )

        async def fake_status_still_executing(
            self, symbol, order_list_id
        ):

            return {"listOrderStatus": "EXECUTING"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with regime_patch, atr_patch:

                with patch.object(
                    BinanceTradingClient,
                    "cancel_order_list",
                    new=fake_cancel_fails
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "get_order_list_status",
                        new=fake_status_still_executing
                    ):

                        await agent._apply_dynamic_take_profit(
                            trade,
                            109.5
                        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.take_profit == 110.0

        assert fresh.take_profit_extended is False

        assert fresh.order_list_id == "777222"

    @pytest.mark.asyncio
    async def test_falls_back_to_emergency_close_when_new_oco_fails(
        self
    ):

        trade = self._live_trade_near_target(
            user_id=60103
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        regime_patch, atr_patch = (
            self._enable_and_mock_gates(agent)
        )

        sell_calls = []

        async def fake_cancel(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        async def fake_oco_fails(self, **kwargs):

            raise BinanceTradingError(
                "simulated exchange rejection"
            )

        async def fake_market_sell(
            self, symbol, side, quantity, client_order_id=None
        ):

            sell_calls.append(
                (symbol, side, quantity)
            )

            return {
                "executedQty": str(quantity),
                "cummulativeQuoteQty": str(quantity * 109.5)
            }

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with regime_patch, atr_patch:

                with patch.object(
                    BinanceTradingClient,
                    "cancel_order_list",
                    new=fake_cancel
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "place_oco_sell_order",
                        new=fake_oco_fails
                    ):

                        with patch.object(
                            BinanceTradingClient,
                            "place_market_order",
                            new=fake_market_sell
                        ):

                            await agent._apply_dynamic_take_profit(
                                trade,
                                109.5
                            )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.status == "CLOSED"

        assert (
            fresh.exit_reason
            ==
            "DYNAMIC_TAKE_PROFIT_EMERGENCY_CLOSE"
        )

        assert len(sell_calls) == 1

    @pytest.mark.asyncio
    async def test_skips_replacement_when_oco_already_resolved(
        self
    ):

        trade = self._live_trade_near_target(
            user_id=60104
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        regime_patch, atr_patch = (
            self._enable_and_mock_gates(agent)
        )

        async def fake_cancel_fails(self, symbol, order_list_id):

            raise BinanceTradingError(
                "Unknown order sent (already filled/canceled)"
            )

        async def fake_status_all_done(self, symbol, order_list_id):

            return {"listOrderStatus": "ALL_DONE"}

        with patch(
            "core.agents.position_manager_agent.settings.MODE",
            "live"
        ):

            with regime_patch, atr_patch:

                with patch.object(
                    BinanceTradingClient,
                    "cancel_order_list",
                    new=fake_cancel_fails
                ):

                    with patch.object(
                        BinanceTradingClient,
                        "get_order_list_status",
                        new=fake_status_all_done
                    ):

                        await agent._apply_dynamic_take_profit(
                            trade,
                            109.5
                        )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.take_profit_extended is False

        assert fresh.order_list_id == "777222"

    @pytest.mark.asyncio
    async def test_paper_trade_dynamic_take_profit_never_calls_binance(
        self
    ):

        trade = _open_trade(
            user_id=60105,
            entry_price=100.0,
            take_profit=110.0
        )

        bus = EventBus()

        agent = PositionManagerAgent(bus)

        regime_patch, atr_patch = (
            self._enable_and_mock_gates(agent)
        )

        async def fail_if_called(*args, **kwargs):

            raise AssertionError(
                "PAPER trade must never call the live Binance client"
            )

        with regime_patch, atr_patch:

            with patch.object(
                BinanceTradingClient,
                "cancel_order_list",
                new=fail_if_called
            ):

                await agent._apply_dynamic_take_profit(
                    trade,
                    109.5
                )

        fresh = trades_repository.get_trade(
            trade.id
        )

        assert fresh.take_profit_extended is True
