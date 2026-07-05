# -*- coding: utf-8 -*-

"""
Unit tests for data/storage/repositories/trades_repository.py
"""

import pytest

from data.storage.repositories.trades_repository import (
    trades_repository
)


class TestCreateTrade:

    def test_creates_trade_with_open_status(self):

        trade = trades_repository.create_trade(
            user_id=1,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        assert trade is not None

        assert trade.status == "OPEN"

        assert trade.entry_price == 100.0

        assert trade.current_price == 100.0

        assert trade.highest_price == 100.0

        assert trade.lowest_price == 100.0

    def test_rejects_invalid_entry_price(self):

        trade = trades_repository.create_trade(
            user_id=1,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=0.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        assert trade is None

    def test_rejects_invalid_quantity(self):

        trade = trades_repository.create_trade(
            user_id=1,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=0.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        assert trade is None

    def test_rejects_negative_entry_price(self):

        trade = trades_repository.create_trade(
            user_id=1,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=-10.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        assert trade is None


class TestHasOpenTrade:

    def test_true_when_open_trade_exists(self):

        trades_repository.create_trade(
            user_id=2,
            symbol="ETHUSDT",
            action="BUY",
            entry_price=2000.0,
            quantity=1.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            trailing_stop=10.0
        )

        assert trades_repository.has_open_trade(
            user_id=2,
            symbol="ETHUSDT"
        ) is True

    def test_false_when_no_open_trade(self):

        assert trades_repository.has_open_trade(
            user_id=999,
            symbol="NONEXISTENT"
        ) is False

    def test_false_after_trade_is_closed(self):

        trade = trades_repository.create_trade(
            user_id=3,
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
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        assert trades_repository.has_open_trade(
            user_id=3,
            symbol="BTCUSDT"
        ) is False


class TestUpdateTradePrice:

    def test_updates_current_price_and_unrealized_pnl(self):

        trade = trades_repository.create_trade(
            user_id=4,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        updated = trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=105.0,
            unrealized_pnl=5.0
        )

        assert updated.current_price == 105.0

        assert updated.unrealized_pnl == 5.0

    def test_updates_highest_price_watermark(self):

        trade = trades_repository.create_trade(
            user_id=5,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=120.0,
            unrealized_pnl=20.0
        )

        # price drops back down; highest_price watermark must remain
        updated = trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=105.0,
            unrealized_pnl=5.0
        )

        assert updated.highest_price == 120.0

        assert updated.lowest_price == 100.0

    def test_rejects_invalid_price(self):

        trade = trades_repository.create_trade(
            user_id=6,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        result = trades_repository.update_trade_price(
            trade_id=trade.id,
            current_price=-5.0,
            unrealized_pnl=0.0
        )

        assert result is None


class TestCloseTrade:

    def test_marks_trade_closed_with_pnl(self):

        trade = trades_repository.create_trade(
            user_id=7,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        closed = trades_repository.close_trade(
            trade_id=trade.id,
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        assert closed.status == "CLOSED"

        assert closed.pnl == 10.0

        assert closed.realized_pnl == 10.0

        assert closed.unrealized_pnl == 0.0

        assert closed.exit_reason == "TAKE_PROFIT"

        assert closed.closed_at is not None

    def test_close_nonexistent_trade_returns_none(self):

        result = trades_repository.close_trade(
            trade_id=999999,
            exit_price=100.0,
            pnl=0.0,
            reason="MANUAL"
        )

        assert result is None


class TestGetOpenAndClosedTrades:

    def test_get_open_trades_returns_only_open(self):

        open_trade = trades_repository.create_trade(
            user_id=8,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        closed_trade = trades_repository.create_trade(
            user_id=8,
            symbol="ETHUSDT",
            action="BUY",
            entry_price=2000.0,
            quantity=1.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            trailing_stop=10.0
        )

        trades_repository.close_trade(
            trade_id=closed_trade.id,
            exit_price=2200.0,
            pnl=200.0,
            reason="TAKE_PROFIT"
        )

        open_trades = trades_repository.get_open_trades(
            user_id=8
        )

        assert len(open_trades) == 1

        assert open_trades[0].id == open_trade.id

    def test_get_closed_trades_returns_only_closed(self):

        trade = trades_repository.create_trade(
            user_id=9,
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
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        closed_trades = trades_repository.get_closed_trades(
            user_id=9
        )

        assert len(closed_trades) == 1

        assert closed_trades[0].status == "CLOSED"


class TestReset:

    """
    Bug fixed: reset() previously deleted EVERY row in the trades
    table for EVERY user, with no filter at all. backtest/runner.py
    and backtest/optimizer/optimizer_engine.py both called it once
    per run to clear their own sandbox trades (user_id=999) before
    each backtest pass, but it silently wiped real paper-trading
    history (user_id=0) along with it every single time either ran.
    """

    def test_reset_clears_only_the_given_users_trades(self):

        trades_repository.create_trade(
            user_id=10,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.reset(
            user_id=10
        )

        assert trades_repository.get_open_trades(
            user_id=10
        ) == []

    def test_reset_does_not_touch_other_users_trades(self):

        # this is the exact regression: user_id=999 (the
        # backtest/optimizer sandbox) resetting must never affect
        # user_id=0 (real paper-trading history) or any other user

        trades_repository.create_trade(
            user_id=999,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.create_trade(
            user_id=0,
            symbol="ETHUSDT",
            action="BUY",
            entry_price=2000.0,
            quantity=1.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            trailing_stop=10.0
        )

        trades_repository.reset(
            user_id=999
        )

        assert trades_repository.get_open_trades(
            user_id=999
        ) == []

        # user_id=0's trade must have survived
        real_user_trades = trades_repository.get_open_trades(
            user_id=0
        )

        assert len(real_user_trades) == 1

        assert real_user_trades[0].symbol == "ETHUSDT"

    def test_reset_requires_user_id(self):

        with pytest.raises(TypeError):

            trades_repository.reset()


class TestResetAll:

    def test_reset_all_clears_every_users_trades(self):

        trades_repository.create_trade(
            user_id=20,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.create_trade(
            user_id=21,
            symbol="ETHUSDT",
            action="BUY",
            entry_price=2000.0,
            quantity=1.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            trailing_stop=10.0
        )

        trades_repository.reset_all()

        assert trades_repository.get_open_trades(
            user_id=20
        ) == []

        assert trades_repository.get_open_trades(
            user_id=21
        ) == []


class TestGetTradesClosedToday:

    def test_empty_with_no_trades(self):

        assert trades_repository.get_trades_closed_today(
            user_id=11
        ) == []

    def test_includes_trades_closed_today(self):

        trade = trades_repository.create_trade(
            user_id=12,
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
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        today_trades = trades_repository.get_trades_closed_today(
            user_id=12
        )

        assert len(today_trades) == 1

        assert today_trades[0].id == trade.id

    def test_does_not_include_open_trades(self):

        trades_repository.create_trade(
            user_id=13,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        assert trades_repository.get_trades_closed_today(
            user_id=13
        ) == []

    def test_does_not_include_other_users_trades(self):

        trade = trades_repository.create_trade(
            user_id=14,
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
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        assert trades_repository.get_trades_closed_today(
            user_id=15
        ) == []


class TestCountTradesOpenedToday:

    def test_zero_with_no_trades(self):

        assert trades_repository.count_trades_opened_today(
            user_id=16
        ) == 0

    def test_counts_trades_created_today_regardless_of_status(self):

        trades_repository.create_trade(
            user_id=17,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trade2 = trades_repository.create_trade(
            user_id=17,
            symbol="ETHUSDT",
            action="BUY",
            entry_price=2000.0,
            quantity=1.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            trailing_stop=10.0
        )

        trades_repository.close_trade(
            trade_id=trade2.id,
            exit_price=2200.0,
            pnl=200.0,
            reason="TAKE_PROFIT"
        )

        # one still open, one closed -- both count, since this
        # tracks "opened today" for overtrading protection, not
        # "closed today"
        assert trades_repository.count_trades_opened_today(
            user_id=17
        ) == 2

    def test_does_not_count_other_users_trades(self):

        trades_repository.create_trade(
            user_id=18,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        assert trades_repository.count_trades_opened_today(
            user_id=19
        ) == 0
