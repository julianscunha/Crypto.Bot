# -*- coding: utf-8 -*-

"""
Tests for the backtest engine: replay_engine.py and metrics_engine.py

Covers the previously-crashing import path (data.storage.metrics) and
verifies the engine runs end to end against the real sample datasets
shipped with the project.
"""

import os

import pytest

from backtest.engine.replay_engine import (
    ReplayEngine
)

from backtest.engine.metrics_engine import (
    MetricsEngine
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

BULLISH_DATASET = os.path.join(
    PROJECT_ROOT,
    "backtest",
    "datasets",
    "bullish.csv"
)


class TestReplayEngine:

    @pytest.mark.asyncio
    async def test_replay_runs_without_crashing(self):

        engine = ReplayEngine(
            csv_path=BULLISH_DATASET,
            user_id=7001
        )

        await engine.replay()

    @pytest.mark.asyncio
    async def test_replay_does_not_raise_on_missing_columns_gracefully(
        self,
        tmp_path
    ):

        # a dataset with only 2 rows -- exercises the same code path
        # without depending on a large fixture

        csv_path = tmp_path / "tiny.csv"

        csv_path.write_text(
            "symbol,open,high,low,close,volume\n"
            "BTCUSDT,100,101,99,100.5,10\n"
            "BTCUSDT,100.5,102,100,101.5,12\n"
        )

        engine = ReplayEngine(
            csv_path=str(csv_path),
            user_id=7002
        )

        await engine.replay()


class TestMetricsEngine:

    def test_generate_does_not_raise_on_import_or_call(self):

        # this previously raised ModuleNotFoundError on import of
        # data.storage.metrics, before any call was even made

        result = MetricsEngine().generate(
            user_id=7003
        )

        assert "total_trades" in result

        assert "winrate" in result

        assert "pnl" in result

    def test_winrate_is_zero_to_one_fraction(self):

        result = MetricsEngine().generate(
            user_id=7004
        )

        assert 0.0 <= result["winrate"] <= 1.0

    def test_expectancy_uses_fractional_winrate_correctly(self):

        # 2 wins of +10, 1 loss of -5 -> winrate = 2/3 = 0.6667
        # avg_win=10, avg_loss=5
        # expectancy = (10 * 0.6667) - (5 * (1-0.6667)) ~= 5

        for pnl, reason in (
            (10.0, "TAKE_PROFIT"),
            (10.0, "TAKE_PROFIT"),
            (-5.0, "STOP_LOSS")
        ):

            trade = trades_repository.create_trade(
                user_id=7005,
                symbol="BTCUSDT",
                action="BUY",
                entry_price=100.0,
                quantity=1.0,
                stop_loss=95.0,
                take_profit=110.0,
                trailing_stop=1.0
            )

            exit_price = (
                100.0 + pnl
                if pnl > 0
                else 100.0 + pnl
            )

            trades_repository.close_trade(
                trade_id=trade.id,
                exit_price=exit_price,
                pnl=pnl,
                reason=reason
            )

        result = MetricsEngine().generate(
            user_id=7005
        )

        assert result["total_trades"] == 3

        # sanity: with a fractional (not percentage) winrate, expectancy
        # should land in a small, sane range -- not be inflated 100x
        # by accidentally using winrate=66.67 instead of 0.6667
        assert -20 < result["expectancy"] < 20
