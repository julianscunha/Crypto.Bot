# -*- coding: utf-8 -*-

"""
Unit tests for core/services/signal_quality_service.py
"""

import pytest

from unittest.mock import patch

from core.services.signal_quality_service import (
    SignalQualityService
)

from core.contracts.messages import (
    StrategySignalPayload
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from data.storage.repositories.portfolio_repository import (
    portfolio_repository
)


def _make_payload(
    user_id=100,
    symbol="BTCUSDT",
    signal_strength=0.9,
    entry_price=100.0
):

    return StrategySignalPayload(
        user_id=user_id,
        symbol=symbol,
        signal="BUY",
        entry_price=entry_price,
        signal_strength=signal_strength
    )


class TestRegisterTrade:

    def test_registers_cooldown_timestamp(self):

        service = SignalQualityService()

        service.register_trade(
            user_id=1,
            symbol="BTCUSDT"
        )

        key = service._build_key(1, "BTCUSDT")

        assert key in service.signal_cooldowns


class TestValidateSignalConfidence:

    def test_high_confidence_passes(self):

        service = SignalQualityService()

        payload = _make_payload(signal_strength=0.9)

        valid, reason = service._validate_signal_confidence(
            payload
        )

        assert valid is True

    def test_low_confidence_fails(self):

        service = SignalQualityService()

        payload = _make_payload(signal_strength=0.1)

        valid, reason = service._validate_signal_confidence(
            payload
        )

        assert valid is False

        assert reason == "LOW_CONFIDENCE"

    def test_missing_signal_strength_defaults_to_zero_and_fails(self):

        service = SignalQualityService()

        payload = StrategySignalPayload(
            user_id=1,
            symbol="BTCUSDT",
            signal="BUY",
            entry_price=100.0
        )

        # default signal_strength is 0.0, below minimum_signal_confidence
        valid, reason = service._validate_signal_confidence(
            payload
        )

        assert valid is False


class TestValidateSignalCooldown:

    def test_passes_when_no_prior_signal(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=200)

        valid, reason = service._validate_signal_cooldown(
            payload
        )

        assert valid is True

        assert reason == "COOLDOWN_READY"

    def test_fails_immediately_after_registering_trade(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=201)

        service.register_trade(
            user_id=201,
            symbol="BTCUSDT"
        )

        valid, reason = service._validate_signal_cooldown(
            payload
        )

        assert valid is False

        assert reason == "SIGNAL_COOLDOWN_ACTIVE"

    def test_disabled_filter_always_passes(self):

        service = SignalQualityService()

        original = service.config["enable_signal_cooldown"]

        try:

            service.config["enable_signal_cooldown"] = False

            payload = _make_payload(user_id=202)

            service.register_trade(
                user_id=202,
                symbol="BTCUSDT"
            )

            valid, reason = service._validate_signal_cooldown(
                payload
            )

            assert valid is True

            assert reason == "FILTER_DISABLED"

        finally:

            service.config[
                "enable_signal_cooldown"
            ] = original


class TestValidatePositionLimit:

    def test_passes_with_no_open_positions(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=300)

        valid, reason = service._validate_position_limit(
            payload
        )

        assert valid is True

    def test_fails_at_maximum_open_positions(self):

        service = SignalQualityService()

        max_positions = service.config[
            "maximum_open_positions"
        ]

        for i in range(max_positions):

            trades_repository.create_trade(
                user_id=301,
                symbol=f"SYMBOL{i}",
                action="BUY",
                entry_price=100.0,
                quantity=1.0,
                stop_loss=95.0,
                take_profit=110.0,
                trailing_stop=1.0
            )

        payload = _make_payload(user_id=301)

        valid, reason = service._validate_position_limit(
            payload
        )

        assert valid is False

        assert reason == "MAXIMUM_OPEN_POSITIONS"


class TestValidateDrawdownProtection:

    def test_passes_with_no_snapshot_yet(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=400)

        valid, reason = service._validate_drawdown_protection(
            payload
        )

        assert valid is True

        assert reason == "PORTFOLIO_WARMUP"

    def test_fails_when_drawdown_exceeds_maximum(self):

        service = SignalQualityService()

        max_drawdown = service.config[
            "maximum_daily_drawdown_percent"
        ]

        portfolio_repository.create_snapshot(
            user_id=401,
            balance=100.0,
            equity=100.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            open_positions=0,
            closed_positions=0,
            exposure=0.0,
            drawdown=max_drawdown + 1.0
        )

        payload = _make_payload(user_id=401)

        valid, reason = service._validate_drawdown_protection(
            payload
        )

        assert valid is False

        assert reason == "MAXIMUM_DRAWDOWN_EXCEEDED"

    def test_passes_when_drawdown_within_limits(self):

        service = SignalQualityService()

        portfolio_repository.create_snapshot(
            user_id=402,
            balance=100.0,
            equity=99.0,
            realized_pnl=0.0,
            unrealized_pnl=-1.0,
            total_pnl=-1.0,
            open_positions=0,
            closed_positions=0,
            exposure=0.0,
            drawdown=0.5
        )

        payload = _make_payload(user_id=402)

        valid, reason = service._validate_drawdown_protection(
            payload
        )

        assert valid is True

    def test_disabled_filter_always_passes(self):

        service = SignalQualityService()

        original = service.config[
            "enable_drawdown_protection"
        ]

        try:

            service.config[
                "enable_drawdown_protection"
            ] = False

            payload = _make_payload(user_id=403)

            valid, reason = service._validate_drawdown_protection(
                payload
            )

            assert valid is True

            assert reason == "FILTER_DISABLED"

        finally:

            service.config[
                "enable_drawdown_protection"
            ] = original


class TestValidateEmaTrend:

    def test_passes_during_warmup(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=500)

        valid, reason = service._validate_ema_trend(
            payload
        )

        assert valid is True

        assert reason == "EMA_WARMUP"

    def test_passes_in_clear_uptrend(self):

        service = SignalQualityService()

        price = 100.0

        for _ in range(30):

            service.trend_service.update_price(
                user_id=501,
                symbol="BTCUSDT",
                price=price
            )

            price += 2.0

        payload = _make_payload(user_id=501)

        valid, reason = service._validate_ema_trend(
            payload
        )

        assert valid is True

    def test_fails_in_clear_downtrend(self):

        service = SignalQualityService()

        price = 200.0

        for _ in range(30):

            service.trend_service.update_price(
                user_id=502,
                symbol="BTCUSDT",
                price=price
            )

            price -= 3.0

        payload = _make_payload(user_id=502)

        valid, reason = service._validate_ema_trend(
            payload
        )

        assert valid is False

        assert reason == "BEARISH_TREND"


class TestValidateMarketRegimeAlignment:

    """
    Bug fixed: enable_market_regime_alignment existed in
    core/config/signal_quality_config.py since early in this
    project, but no code anywhere ever read it.
    core.services.market_regime_service already runs
    unconditionally inside AnalystAgent every candle -- it was
    already computing BULLISH/BEARISH/TRENDING/SIDEWAYS per symbol,
    just never connected to any gating decision.

    Disabled by default -- enabling it is opt-in and changes zero
    behavior until a person deliberately turns it on. Only blocks
    on BEARISH specifically: this codebase is long-only (every
    signal this validator ever sees is a BUY), so BEARISH is the
    only regime that directly contradicts the position's possible
    direction. SIDEWAYS/TRENDING/BULLISH must all pass through.
    """

    def test_disabled_filter_always_passes(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=900)

        valid, reason = (

            service
            ._validate_market_regime_alignment(
                payload
            )
        )

        assert valid is True

        assert reason == "FILTER_DISABLED"

    def test_unknown_regime_passes_as_warmup(self):

        service = SignalQualityService()

        service.config[
            "enable_market_regime_alignment"
        ] = True

        payload = _make_payload(user_id=901)

        with patch.object(
            service.market_regime,
            "detect_regime",
            return_value="UNKNOWN"
        ):

            valid, reason = (

                service
                ._validate_market_regime_alignment(
                    payload
                )
            )

        assert valid is True

        assert reason == "REGIME_WARMUP"

    def test_bearish_regime_blocks_the_signal(self):

        service = SignalQualityService()

        service.config[
            "enable_market_regime_alignment"
        ] = True

        payload = _make_payload(user_id=902)

        with patch.object(
            service.market_regime,
            "detect_regime",
            return_value="BEARISH"
        ):

            valid, reason = (

                service
                ._validate_market_regime_alignment(
                    payload
                )
            )

        assert valid is False

        assert reason == "BEARISH_REGIME"

    @pytest.mark.parametrize(
        "regime",
        [
            "BULLISH",
            "SIDEWAYS",
            "TRENDING"
        ]
    )
    def test_non_bearish_regimes_pass(
        self,
        regime
    ):

        service = SignalQualityService()

        service.config[
            "enable_market_regime_alignment"
        ] = True

        payload = _make_payload(user_id=903)

        with patch.object(
            service.market_regime,
            "detect_regime",
            return_value=regime
        ):

            valid, reason = (

                service
                ._validate_market_regime_alignment(
                    payload
                )
            )

        assert valid is True

        assert reason == "REGIME_ALIGNED"

    def test_full_pipeline_blocks_buy_signal_during_real_bearish_trend(
        self
    ):

        from core.services.market_regime_service import (
            market_regime_service
        )

        service = SignalQualityService()

        service.config[
            "enable_market_regime_alignment"
        ] = True

        # uses a uniquely-named symbol, not BTCUSDT -- market_regime_
        # service is a module-level singleton shared across every
        # test in this suite, so feeding real price history under a
        # commonly-used symbol here would leak BEARISH regime state
        # into other tests that use the same symbol and don't expect
        # this filter to be active
        symbol = "REGIMETESTUSDT"

        price = 100.0

        for _ in range(25):

            price -= 0.5

            market_regime_service.update_price(
                symbol=symbol,
                close=price
            )

        payload = _make_payload(
            user_id=904,
            symbol=symbol,
            signal_strength=0.95
        )

        valid, reason = service.validate(
            payload
        )

        assert valid is False

        assert reason == "BEARISH_REGIME"


class TestValidateMarketVolatility:

    def test_passes_during_warmup(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=600)

        valid, reason = service._validate_market_volatility(
            payload
        )

        assert valid is True

        assert reason == "ATR_WARMUP"

    def test_fails_with_low_volatility(self):

        service = SignalQualityService()

        # near-flat candles -> very low ATR%
        for _ in range(20):

            service.atr_service.update_candle(
                user_id=601,
                symbol="BTCUSDT",
                high=100.001,
                low=99.999,
                close=100.0
            )

        payload = _make_payload(user_id=601)

        valid, reason = service._validate_market_volatility(
            payload
        )

        assert valid is False

        assert reason == "LOW_VOLATILITY"

    def test_passes_with_sufficient_volatility(self):

        service = SignalQualityService()

        price = 100.0

        for _ in range(20):

            service.atr_service.update_candle(
                user_id=602,
                symbol="BTCUSDT",
                high=price + 5,
                low=price - 5,
                close=price
            )

            price += 1.0

        payload = _make_payload(user_id=602)

        valid, reason = service._validate_market_volatility(
            payload
        )

        assert valid is True


class TestValidatePipeline:

    def test_full_validate_passes_for_clean_signal(self):

        service = SignalQualityService()

        # warm up trend and volatility so only confidence/cooldown/
        # position-limit/drawdown remain (all warmup-pass by default)
        valid, reason = service.validate(
            _make_payload(
                user_id=700,
                signal_strength=0.9
            )
        )

        assert valid is True

        assert reason == "VALID"

    def test_full_validate_fails_for_low_confidence_signal(self):

        service = SignalQualityService()

        valid, reason = service.validate(
            _make_payload(
                user_id=701,
                signal_strength=0.05
            )
        )

        assert valid is False

        assert reason == "LOW_CONFIDENCE"


class TestValidateDailyLossLimit:

    def test_passes_with_no_trades_today(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=800)

        valid, reason = service._validate_daily_loss_limit(
            payload
        )

        assert valid is True

    def test_fails_when_daily_loss_exceeds_configured_percent(self):

        from core.config.trading_config import TRADING_CONFIG

        service = SignalQualityService()

        account_balance = TRADING_CONFIG["account_balance"]

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        loss_amount = (
            account_balance
            *
            (max_loss_percent + 5)
            / 100
        )

        trade = trades_repository.create_trade(
            user_id=801,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.close_trade(
            trade_id=trade.id,
            exit_price=100.0 - loss_amount,
            pnl=-loss_amount,
            reason="STOP_LOSS"
        )

        payload = _make_payload(user_id=801)

        valid, reason = service._validate_daily_loss_limit(
            payload
        )

        assert valid is False

        assert reason == "DAILY_LOSS_LIMIT_REACHED"

    def test_disabled_filter_always_passes(self):

        service = SignalQualityService()

        original = service.config[
            "enable_daily_loss_limit"
        ]

        try:

            service.config[
                "enable_daily_loss_limit"
            ] = False

            payload = _make_payload(user_id=802)

            valid, reason = service._validate_daily_loss_limit(
                payload
            )

            assert valid is True

            assert reason == "FILTER_DISABLED"

        finally:

            service.config[
                "enable_daily_loss_limit"
            ] = original


class TestValidateDailyTradeLimit:

    def test_passes_with_no_trades_today(self):

        service = SignalQualityService()

        payload = _make_payload(user_id=810)

        valid, reason = service._validate_daily_trade_limit(
            payload
        )

        assert valid is True

    def test_fails_at_max_daily_trades(self):

        from core.config.trading_config import TRADING_CONFIG

        service = SignalQualityService()

        max_daily_trades = (
            TRADING_CONFIG["max_daily_trades"]
        )

        for _ in range(max_daily_trades):

            trade = trades_repository.create_trade(
                user_id=811,
                symbol="BTCUSDT",
                action="BUY",
                entry_price=100.0,
                quantity=1.0,
                stop_loss=95.0,
                take_profit=110.0,
                trailing_stop=1.0
            )

            trades_repository.close_trade(
                trade_id=trade.id,
                exit_price=101.0,
                pnl=1.0,
                reason="TAKE_PROFIT"
            )

        payload = _make_payload(user_id=811)

        valid, reason = service._validate_daily_trade_limit(
            payload
        )

        assert valid is False

        assert reason == "DAILY_TRADE_LIMIT_REACHED"

    def test_disabled_filter_always_passes(self):

        service = SignalQualityService()

        original = service.config[
            "enable_daily_trade_limit"
        ]

        try:

            service.config[
                "enable_daily_trade_limit"
            ] = False

            payload = _make_payload(user_id=812)

            valid, reason = service._validate_daily_trade_limit(
                payload
            )

            assert valid is True

            assert reason == "FILTER_DISABLED"

        finally:

            service.config[
                "enable_daily_trade_limit"
            ] = original


class TestValidatePipelineDailyLimits:

    def test_full_validate_fails_when_daily_loss_limit_reached(
        self
    ):

        from core.config.trading_config import TRADING_CONFIG

        service = SignalQualityService()

        account_balance = TRADING_CONFIG["account_balance"]

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        loss_amount = (
            account_balance
            *
            (max_loss_percent + 5)
            / 100
        )

        trade = trades_repository.create_trade(
            user_id=820,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.close_trade(
            trade_id=trade.id,
            exit_price=100.0 - loss_amount,
            pnl=-loss_amount,
            reason="STOP_LOSS"
        )

        valid, reason = service.validate(
            _make_payload(
                user_id=820,
                signal_strength=0.9
            )
        )

        assert valid is False

        assert reason == "DAILY_LOSS_LIMIT_REACHED"
