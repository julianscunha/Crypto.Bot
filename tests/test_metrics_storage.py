# -*- coding: utf-8 -*-

"""
Regression tests for data/storage/metrics.py

Bugs fixed:
1. backtest/engine/metrics_engine.py imported data.storage.metrics.MetricsStorage,
   which did not exist anywhere in the codebase -> ModuleNotFoundError on import,
   meaning the entire backtest/optimizer pipeline could never run.
2. TradeMetricsService.get_metrics() returns winrate as a 0-100 percentage, but
   backtest/reports/validation_interpreter.py and backtest/optimizer/optimizer_engine.py
   both treat winrate as a 0-1 fraction (compared against 0.40/0.55, formatted as :.2%).
   MetricsStorage normalizes this at the source so every consumer shares one convention.
"""

from data.storage.metrics import (
    MetricsStorage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


class TestMetricsStorageImport:

    def test_module_imports_without_error(self):

        storage = MetricsStorage()

        assert storage is not None


class TestGetMetricsShape:

    def test_get_metrics_returns_required_keys(self):

        storage = MetricsStorage()

        metrics = storage.get_metrics(user_id=1)

        for key in (
            "total_trades",
            "winrate",
            "pnl"
        ):

            assert key in metrics

    def test_winrate_is_zero_to_one_fraction_with_no_trades(self):

        storage = MetricsStorage()

        metrics = storage.get_metrics(user_id=1)

        assert metrics["total_trades"] == 0

        assert 0.0 <= metrics["winrate"] <= 1.0

    def test_winrate_normalized_to_fraction_with_winning_trades(self):

        # 2 wins, 0 losses -> TradeMetricsService reports winrate=100.0
        # (0-100 scale); MetricsStorage must normalize that to 1.0

        for _ in range(2):

            trade = trades_repository.create_trade(
                user_id=2,
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

        storage = MetricsStorage()

        metrics = storage.get_metrics(user_id=2)

        assert metrics["total_trades"] == 2

        assert metrics["winrate"] == 1.0

    def test_winrate_normalized_with_mixed_trades(self):

        # 1 win, 1 loss -> 50% winrate -> normalized 0.5

        winner = trades_repository.create_trade(
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
            trade_id=winner.id,
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        loser = trades_repository.create_trade(
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
            trade_id=loser.id,
            exit_price=95.0,
            pnl=-5.0,
            reason="STOP_LOSS"
        )

        storage = MetricsStorage()

        metrics = storage.get_metrics(user_id=3)

        assert metrics["total_trades"] == 2

        assert metrics["winrate"] == 0.5
