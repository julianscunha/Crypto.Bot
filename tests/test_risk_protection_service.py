# -*- coding: utf-8 -*-

"""
Unit tests for core/services/risk_protection_service.py

Bug fixed: max_daily_loss_percent and max_daily_trades already
existed in core/config/trading_config.py with sane defaults and
appeared in .env, but no code anywhere actually read or enforced
them. This service is what makes them real, gating new signals via
core/services/signal_quality_service.py's validate() pipeline (see
test_signal_quality_service.py for the integration-level coverage).
"""

from core.services.risk_protection_service import (
    RiskProtectionService
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


def _open_and_close(
    user_id,
    pnl,
    reason="TAKE_PROFIT"
):

    trade = trades_repository.create_trade(
        user_id=user_id,
        symbol="BTCUSDT",
        action="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0,
        trailing_stop=1.0
    )

    return trades_repository.close_trade(
        trade_id=trade.id,
        exit_price=100.0 + pnl,
        pnl=pnl,
        reason=reason
    )


class TestGetDailyRealizedPnl:

    def test_zero_with_no_trades(self):

        service = RiskProtectionService()

        assert service.get_daily_realized_pnl(
            user_id=20001
        ) == 0.0

    def test_sums_todays_closed_trades(self):

        service = RiskProtectionService()

        _open_and_close(20002, 10.0)

        _open_and_close(20002, -3.0)

        assert service.get_daily_realized_pnl(
            user_id=20002
        ) == 7.0

    def test_does_not_count_other_users_trades(self):

        service = RiskProtectionService()

        _open_and_close(20003, 100.0)

        assert service.get_daily_realized_pnl(
            user_id=20004
        ) == 0.0


class TestGetDailyTradeCount:

    def test_zero_with_no_trades(self):

        service = RiskProtectionService()

        assert service.get_daily_trade_count(
            user_id=20005
        ) == 0

    def test_counts_trades_opened_today(self):

        service = RiskProtectionService()

        _open_and_close(20006, 5.0)

        _open_and_close(20006, 5.0)

        _open_and_close(20006, 5.0)

        assert service.get_daily_trade_count(
            user_id=20006
        ) == 3


class TestCheckDailyLossLimit:

    def test_allows_when_no_trades_today(self):

        service = RiskProtectionService()

        allowed, reason = service.check_daily_loss_limit(
            user_id=20007,
            account_balance=100.0
        )

        assert allowed is True

        assert reason == "NO_DAILY_LOSS"

    def test_allows_profitable_day_regardless_of_size(self):

        service = RiskProtectionService()

        _open_and_close(20008, 1000.0)

        allowed, reason = service.check_daily_loss_limit(
            user_id=20008,
            account_balance=10.0
        )

        assert allowed is True

        assert reason == "NO_DAILY_LOSS"

    def test_blocks_when_loss_exceeds_configured_percent(self):

        service = RiskProtectionService()

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        account_balance = 100.0

        # lose exactly 1% more than the configured limit
        loss_amount = (
            account_balance
            *
            (max_loss_percent + 1)
            / 100
        )

        _open_and_close(20009, -loss_amount)

        allowed, reason = service.check_daily_loss_limit(
            user_id=20009,
            account_balance=account_balance
        )

        assert allowed is False

        assert reason == "DAILY_LOSS_LIMIT_REACHED"

    def test_allows_when_loss_is_within_configured_percent(self):

        service = RiskProtectionService()

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        account_balance = 100.0

        # lose half of the allowed limit
        loss_amount = (
            account_balance
            *
            (max_loss_percent / 2)
            / 100
        )

        _open_and_close(20010, -loss_amount)

        allowed, reason = service.check_daily_loss_limit(
            user_id=20010,
            account_balance=account_balance
        )

        assert allowed is True

        assert reason == "WITHIN_DAILY_LOSS_LIMIT"

    def test_zero_account_balance_does_not_crash(self):

        service = RiskProtectionService()

        allowed, reason = service.check_daily_loss_limit(
            user_id=20011,
            account_balance=0.0
        )

        assert allowed is True

        assert reason == "ACCOUNT_BALANCE_WARMUP"


class TestCheckDailyTradeLimit:

    def test_allows_below_limit(self):

        service = RiskProtectionService()

        max_trades = (
            TRADING_CONFIG["max_daily_trades"]
        )

        for _ in range(max_trades - 1):

            _open_and_close(20012, 1.0)

        allowed, reason = service.check_daily_trade_limit(
            user_id=20012
        )

        assert allowed is True

        assert reason == "WITHIN_DAILY_TRADE_LIMIT"

    def test_blocks_at_limit(self):

        service = RiskProtectionService()

        max_trades = (
            TRADING_CONFIG["max_daily_trades"]
        )

        for _ in range(max_trades):

            _open_and_close(20013, 1.0)

        allowed, reason = service.check_daily_trade_limit(
            user_id=20013
        )

        assert allowed is False

        assert reason == "DAILY_TRADE_LIMIT_REACHED"

    def test_blocks_even_when_all_trades_were_profitable(self):

        # overtrading protection must not be bypassed by a winning
        # streak -- frequency itself is the risk being managed here
        service = RiskProtectionService()

        max_trades = (
            TRADING_CONFIG["max_daily_trades"]
        )

        for _ in range(max_trades):

            _open_and_close(20014, 50.0, reason="TAKE_PROFIT")

        allowed, _ = service.check_daily_trade_limit(
            user_id=20014
        )

        assert allowed is False


class TestGetStatus:

    def test_shape_with_no_activity(self):

        service = RiskProtectionService()

        status = service.get_status(
            user_id=20015,
            account_balance=100.0
        )

        assert status["trading_halted"] is False

        assert status["halt_reason"] is None

        assert status["daily_pnl"] == 0.0

        assert status["daily_trade_count"] == 0

    def test_reports_halted_with_reason_on_loss_breach(self):

        service = RiskProtectionService()

        account_balance = 100.0

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        loss_amount = (
            account_balance
            *
            (max_loss_percent + 5)
            / 100
        )

        _open_and_close(20016, -loss_amount)

        status = service.get_status(
            user_id=20016,
            account_balance=account_balance
        )

        assert status["trading_halted"] is True

        assert status["halt_reason"] == "DAILY_LOSS_LIMIT_REACHED"

        assert status["daily_loss_percent"] > 0

    def test_halt_reason_is_the_loss_limit_when_only_that_is_breached(
        self
    ):

        service = RiskProtectionService()

        account_balance = 100.0

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        loss_amount = (
            account_balance
            *
            (max_loss_percent + 5)
            / 100
        )

        # a single loss that breaches the loss limit, with no other
        # trades today -- isolates the loss check from the trade
        # count check entirely (1 trade is nowhere near
        # max_daily_trades)
        _open_and_close(20017, -loss_amount)

        status = service.get_status(
            user_id=20017,
            account_balance=account_balance
        )

        assert status["trading_halted"] is True

        assert status["halt_reason"] == "DAILY_LOSS_LIMIT_REACHED"

        assert status["daily_trade_count"] == 1
