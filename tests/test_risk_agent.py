# -*- coding: utf-8 -*-

"""
Unit tests for core/agents/risk_agent.py's own logic, isolated from
the full pipeline (tests/test_pipeline_integration.py only exercises
the happy path end to end; tests/test_risk_agent_telemetry.py only
covers market_state telemetry on rejection).

Covers:
- _apply_exposure_limit's clamp branch (position_notional over the
  max exposure allowed by account_balance).
- _calculate_position_size's use of exchange_filters.get_filters
  per-symbol quantity precision vs. the EXCHANGE_CONFIG fallback.
- _calculate_position_size/_calculate_risk_levels behavior when
  risk_distance is zero or negative.
- _validate_signal's INVALID_USER_ID and SYMBOL_NOT_ALLOWED branches.
"""

import pytest

from core.agents.risk_agent import RiskAgent

from core.contracts.messages import StrategySignalPayload

from core.bus.event_bus import EventBus

from core.config.trading_config import TRADING_CONFIG

from core.config.exchange_config import EXCHANGE_CONFIG

from core.services import exchange_filters as exchange_filters_module


def _make_payload(
    user_id=600,
    symbol="BTCUSDT",
    signal="BUY",
    entry_price=100.0,
    atr=2.0
):

    return StrategySignalPayload(
        user_id=user_id,
        symbol=symbol,
        signal=signal,
        entry_price=entry_price,
        atr=atr
    )


@pytest.fixture
def agent():

    return RiskAgent(EventBus())


class TestApplyExposureLimit:

    def test_clamps_quantity_when_notional_exceeds_max_exposure(
        self,
        agent,
        monkeypatch
    ):

        # account_balance=1000, max_position_exposure_percent=25 ->
        # maximum_position_value = 250.0. entry_price=100, quantity=10
        # -> notional=1000, well over the 250 cap, so the clamp branch
        # must kick in and return maximum_position_value / entry_price.
        monkeypatch.setitem(
            TRADING_CONFIG,
            "account_balance",
            1000.0
        )

        monkeypatch.setitem(
            TRADING_CONFIG,
            "max_position_exposure_percent",
            25.0
        )

        adjusted = agent._apply_exposure_limit(
            entry_price=100.0,
            quantity=10.0
        )

        expected = round(
            250.0 / 100.0,
            EXCHANGE_CONFIG["quantity_precision"]
        )

        assert adjusted == expected

        assert adjusted < 10.0

    def test_returns_original_quantity_when_within_limit(
        self,
        agent,
        monkeypatch
    ):

        monkeypatch.setitem(
            TRADING_CONFIG,
            "account_balance",
            1000.0
        )

        monkeypatch.setitem(
            TRADING_CONFIG,
            "max_position_exposure_percent",
            25.0
        )

        # notional = 1 * 100 = 100, under the 250 cap -> untouched.
        adjusted = agent._apply_exposure_limit(
            entry_price=100.0,
            quantity=1.0
        )

        assert adjusted == 1.0


class TestCalculatePositionSize:

    def test_uses_symbol_precision_from_exchange_filters_when_present(
        self,
        agent,
        monkeypatch
    ):

        monkeypatch.setitem(
            exchange_filters_module._cache,
            "BTCUSDT",
            {**exchange_filters_module._DEFAULTS, "qty_precision": 1}
        )

        monkeypatch.setitem(
            TRADING_CONFIG,
            "account_balance",
            1000.0
        )

        monkeypatch.setitem(
            TRADING_CONFIG,
            "risk_per_trade_percent",
            1.0
        )

        quantity = agent._calculate_position_size(
            risk_distance=3.0,
            symbol="BTCUSDT"
        )

        # risk_amount = 1000 * 0.01 = 10; 10/3 = 3.333... rounded to
        # qty_precision=1 (from the symbol's cached filters) -> 3.3,
        # not EXCHANGE_CONFIG["quantity_precision"] (default 4).
        assert quantity == round(10.0 / 3.0, 1)

    def test_falls_back_to_exchange_config_precision_without_symbol(
        self,
        agent,
        monkeypatch
    ):

        monkeypatch.setitem(
            TRADING_CONFIG,
            "account_balance",
            1000.0
        )

        monkeypatch.setitem(
            TRADING_CONFIG,
            "risk_per_trade_percent",
            1.0
        )

        quantity = agent._calculate_position_size(
            risk_distance=3.0,
            symbol=""
        )

        assert quantity == round(
            10.0 / 3.0,
            EXCHANGE_CONFIG["quantity_precision"]
        )

    def test_raises_zero_division_error_when_risk_distance_is_zero(
        self,
        agent
    ):

        # Documents current behavior: _calculate_position_size has no
        # guard against risk_distance == 0. In the real on_message
        # flow this is unreachable because _calculate_risk_levels
        # already rejects risk_distance <= 0 (returns None) before
        # _calculate_position_size is ever called -- but calling it
        # directly with 0 (as this test does) raises, uncaught.
        with pytest.raises(ZeroDivisionError):

            agent._calculate_position_size(
                risk_distance=0.0,
                symbol="BTCUSDT"
            )

    def test_returns_zero_when_risk_distance_is_negative(
        self,
        agent
    ):

        # A negative risk_distance flips the division to a negative
        # quantity, which the final max(quantity, 0.0) clamps to 0.0
        # rather than raising -- unlike the zero case above.
        quantity = agent._calculate_position_size(
            risk_distance=-3.0,
            symbol="BTCUSDT"
        )

        assert quantity == 0.0


class TestCalculateRiskLevels:

    def test_returns_none_when_risk_distance_would_be_zero(
        self,
        agent
    ):

        # atr=0 -> stop_loss == entry_price exactly, which the
        # "stop_loss >= entry_price" guard already rejects by
        # returning None (this path is normally unreachable via
        # on_message, since _validate_signal blocks atr <= 0 first).
        payload = _make_payload(
            entry_price=100.0,
            atr=0.0
        )

        result = agent._calculate_risk_levels(
            payload,
            entry_price=100.0
        )

        assert result is None


class TestValidateSignal:

    def test_invalid_user_id_when_not_an_int(
        self,
        agent
    ):

        payload = _make_payload(
            user_id="not-an-int"
        )

        valid, reason = agent._validate_signal(payload)

        assert valid is False

        assert reason == "INVALID_USER_ID"

    def test_invalid_user_id_when_negative(
        self,
        agent
    ):

        payload = _make_payload(
            user_id=-1
        )

        valid, reason = agent._validate_signal(payload)

        assert valid is False

        assert reason == "INVALID_USER_ID"

    def test_symbol_not_allowed_when_outside_settings_symbols(
        self,
        agent
    ):

        payload = _make_payload(
            symbol="DOGEUSDT"
        )

        valid, reason = agent._validate_signal(payload)

        assert valid is False

        assert reason == "SYMBOL_NOT_ALLOWED"

    def test_valid_signal_passes(
        self,
        agent
    ):

        payload = _make_payload()

        valid, reason = agent._validate_signal(payload)

        assert valid is True

        assert reason == "VALID"
