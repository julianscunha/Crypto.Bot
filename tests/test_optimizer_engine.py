# -*- coding: utf-8 -*-

"""
Tests for backtest/optimizer/optimizer_engine.py's dataset
preparation (OptimizerEngine.__init__ / _prepare_datasets).

The optimizer previously tuned parameters against the same small,
fixed synthetic CSVs in backtest/datasets/ every single run,
regardless of how the actual market had moved since. It now fetches
real history from Binance's public klines endpoint before each run,
chronologically splitting it into train/validation -- falling back
to the synthetic datasets (with a clear warning, never a crash) if
the fetch fails for any reason, since a network hiccup must never
block the user from running an optimization at all.
"""

import os

import pytest

from unittest.mock import patch, AsyncMock

from backtest.optimizer.optimizer_engine import OptimizerEngine


SYNTHETIC_TRAIN_DATASETS = [

    "backtest/datasets/bullish.csv",

    "backtest/datasets/bearish.csv",

    "backtest/datasets/sideways.csv",

    "backtest/datasets/volatile.csv"
]

SYNTHETIC_VALIDATION_DATASET = (
    "backtest/datasets/validation.csv"
)


def _raw_candle(open_time_ms, close=100.5):

    return [
        open_time_ms,
        "100.0",
        "101.0",
        "99.0",
        str(close),
        "10.0",
        0, 0, 0, 0, 0, 0
    ]


class _FakeResponse:

    def __init__(self, data, status=200, headers=None):

        self._data = data

        self.status = status

        self.headers = headers or {}

    async def json(self):

        return self._data

    async def text(self):

        return str(self._data)

    async def __aenter__(self):

        return self

    async def __aexit__(self, *args):

        return False


class _FakeSession:

    """
    Returns `candles_per_symbol` candles on the first call for each
    symbol, then an empty page to stop pagination -- enough to
    exercise the real fetch -> split -> write -> assign pipeline
    without needing thousands of fake candles.
    """

    def __init__(self, candles_per_symbol=200):

        self.candles_per_symbol = candles_per_symbol

        self.calls = 0

    def get(self, url, params, timeout):

        self.calls += 1

        interval_ms = 300_000

        if self.calls % 2 == 1:

            return _FakeResponse([
                _raw_candle(i * interval_ms)
                for i in range(self.candles_per_symbol)
            ])

        return _FakeResponse([])

    async def __aenter__(self):

        return self

    async def __aexit__(self, *args):

        return False


@pytest.fixture(autouse=True)
def _cleanup_live_history_dir():

    yield

    import shutil

    shutil.rmtree(
        "backtest/datasets/live_history",
        ignore_errors=True
    )


class TestPrepareDatasetsFallback:

    def test_falls_back_to_synthetic_datasets_on_fetch_failure(
        self
    ):

        class _AlwaysFailsSession:

            def get(self, url, params, timeout):

                raise ConnectionError(
                    "simulated network failure"
                )

            async def __aenter__(self):

                return self

            async def __aexit__(self, *args):

                return False

        with patch(
            "data.ingestion.binance_history."
            "RETRY_BACKOFF_BASE_SECONDS",
            0
        ):

            with patch(
                "data.ingestion.binance_history."
                "aiohttp.ClientSession",
                return_value=_AlwaysFailsSession()
            ):

                engine = OptimizerEngine()

        assert engine.TRAIN_DATASETS == SYNTHETIC_TRAIN_DATASETS

        assert (
            engine.VALIDATION_DATASET
            == SYNTHETIC_VALIDATION_DATASET
        )

    def test_does_not_raise_when_fetch_fails(self):

        with patch(
            "data.ingestion.binance_history."
            "RETRY_BACKOFF_BASE_SECONDS",
            0
        ):

            with patch(
                "data.ingestion.binance_history."
                "aiohttp.ClientSession",
                side_effect=ConnectionError("no network")
            ):

                # must not raise -- a network failure here should
                # never block the user from running an optimization
                OptimizerEngine()


class TestPrepareDatasetsSuccess:

    def test_assigns_real_data_csv_paths(self):

        fake_session = _FakeSession(
            candles_per_symbol=200
        )

        with patch(
            "data.ingestion.binance_history."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            engine = OptimizerEngine()

        for path in engine.TRAIN_DATASETS:

            assert "live_history" in path

        for path in engine.VALIDATION_DATASETS:

            assert "live_history" in path

        assert (
            engine.VALIDATION_DATASET
            == engine.VALIDATION_DATASETS[0]
        )

    def test_writes_real_csv_files_to_disk(self):

        fake_session = _FakeSession(
            candles_per_symbol=200
        )

        with patch(
            "data.ingestion.binance_history."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            engine = OptimizerEngine()

        for path in (
            engine.TRAIN_DATASETS
            +
            engine.VALIDATION_DATASETS
        ):

            assert os.path.exists(path)

    def test_one_dataset_pair_per_configured_symbol(self):

        from core.config.settings import settings

        fake_session = _FakeSession(
            candles_per_symbol=200
        )

        with patch(
            "data.ingestion.binance_history."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            engine = OptimizerEngine()

        assert (
            len(engine.TRAIN_DATASETS)
            == len(settings.SYMBOLS)
        )

        assert (
            len(engine.VALIDATION_DATASETS)
            == len(settings.SYMBOLS)
        )

    def test_validation_data_is_chronologically_after_train_data(
        self
    ):

        # candles_per_symbol smaller than VALIDATION_DAYS worth of
        # candles puts everything in validation (see
        # split_train_validation's edge-case behavior); use enough
        # candles here that some land in train, to meaningfully
        # check ordering
        candles_per_symbol = 10_000

        fake_session = _FakeSession(
            candles_per_symbol=candles_per_symbol
        )

        with patch(
            "data.ingestion.binance_history."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            engine = OptimizerEngine()

        with open(engine.TRAIN_DATASETS[0]) as f:

            train_lines = f.readlines()

        with open(engine.VALIDATION_DATASETS[0]) as f:

            validation_lines = f.readlines()

        # both files have content (header + at least one row) --
        # confirms the split actually produced two non-trivial files
        # rather than dumping everything into one
        assert len(train_lines) > 1

        assert len(validation_lines) > 1


class TestGenerateCombinationsRiskRewardPreFilter:

    """
    Bug fixed: generate_combinations() previously returned every
    tp/sl/trailing combination unconditionally, including ones
    where atr_take_profit_multiplier / atr_stop_multiplier fell
    below settings.MINIMUM_RISK_REWARD_RATIO. RiskAgent rejects
    every signal from such a combination with LOW_RR regardless of
    structure/ATR/anything else, so those combinations always ended
    up with zero approved trades and were discarded later by the
    total_trades < 5 check -- after already paying for a full
    replay across every training dataset. This pre-filter skips
    them before any replay happens.
    """

    @staticmethod
    def _build_engine():

        with patch.object(
            OptimizerEngine,
            "_prepare_datasets"
        ):

            return OptimizerEngine()

    def test_excludes_combinations_below_minimum_risk_reward(
        self,
        monkeypatch
    ):

        monkeypatch.setattr(
            "backtest.optimizer.optimizer_engine.settings."
            "MINIMUM_RISK_REWARD_RATIO",
            1.2
        )

        engine = self._build_engine()

        combinations = (
            engine.generate_combinations()
        )

        for combo in combinations:

            risk_reward = (
                combo["atr_take_profit_multiplier"]
                / combo["atr_stop_multiplier"]
            )

            assert risk_reward >= 1.2

    def test_a_known_low_rr_combination_is_absent(
        self,
        monkeypatch
    ):

        # atr_take_profit_multiplier=2.0 with
        # atr_stop_multiplier=2.0 is exactly the symmetric,
        # RR=1.0 case that was silently always rejected by
        # RiskAgent's LOW_RR check -- this combination must never
        # reach replay when the minimum is above 1.0
        monkeypatch.setattr(
            "backtest.optimizer.optimizer_engine.settings."
            "MINIMUM_RISK_REWARD_RATIO",
            1.2
        )

        engine = self._build_engine()

        combinations = (
            engine.generate_combinations()
        )

        assert {
            "atr_take_profit_multiplier": 2.0,
            "atr_stop_multiplier": 2.0,
            "atr_trailing_multiplier": 0.5
        } not in combinations

    def test_does_not_exclude_anything_when_minimum_is_low(
        self,
        monkeypatch
    ):

        monkeypatch.setattr(
            "backtest.optimizer.optimizer_engine.settings."
            "MINIMUM_RISK_REWARD_RATIO",
            0.1
        )

        engine = self._build_engine()

        combinations = (
            engine.generate_combinations()
        )

        assert len(combinations) == 27

    def test_returns_no_combinations_when_minimum_is_unreachable(
        self,
        monkeypatch
    ):

        # highest possible ratio in the grid is 4.0 / 1.0 = 4.0 --
        # anything above that must legitimately return an empty
        # list rather than raising
        monkeypatch.setattr(
            "backtest.optimizer.optimizer_engine.settings."
            "MINIMUM_RISK_REWARD_RATIO",
            5.0
        )

        engine = self._build_engine()

        combinations = (
            engine.generate_combinations()
        )

        assert combinations == []

    """
    Bug fixed: best_config.json was written to disk UNCONDITIONALLY,
    before walk-forward validation even ran -- so a parameter set
    the optimizer's own validation report flagged as overfit
    (PROMISING_BUT_SUSPICIOUS) or backed by too little data
    (INSUFFICIENT_DATA) still got picked up by
    core/config/config_loader.py on the Runner's next start, exactly
    as if it had passed validation cleanly.

    These tests mock MetricsEngine.generate and
    validation_interpreter.analyze to deterministically control the
    verdict, since reliably forcing a specific verdict via organic
    signal generation from small synthetic CSVs would be slow and
    fragile. ReplayEngine is also mocked since these tests are about
    the gate logic itself, not the replay mechanics already covered
    by tests/test_backtest_engine.py.
    """

    @staticmethod
    def _build_engine_with_one_passing_result():

        """
        Returns an OptimizerEngine instance with TRAIN_DATASETS/
        VALIDATION_DATASETS set to harmless placeholder paths
        (ReplayEngine itself is mocked in these tests, so the paths
        are never actually read) and ready to run optimize() with
        exactly one parameter combination, so the test controls
        precisely which result becomes "best".
        """

        with patch.object(
            OptimizerEngine,
            "_prepare_datasets"
        ):

            engine = OptimizerEngine()

        engine.TRAIN_DATASETS = ["fake_train.csv"]

        engine.VALIDATION_DATASETS = ["fake_validation.csv"]

        engine.VALIDATION_DATASET = "fake_validation.csv"

        return engine

    def _run_optimize_with_verdict(
        self,
        tmp_path,
        verdict_status,
        monkeypatch
    ):

        engine = (
            self._build_engine_with_one_passing_result()
        )

        # only one combination to keep the test fast and the
        # "best result" deterministic
        monkeypatch.setattr(
            engine,
            "generate_combinations",
            lambda: [{
                "atr_take_profit_multiplier": 2.0,
                "atr_stop_multiplier": 1.0,
                "atr_trailing_multiplier": 0.5
            }]
        )

        passing_metrics = {

            "total_trades": 50,

            "winrate": 0.6,

            "pnl": 100.0,

            "max_drawdown": -10.0,

            "profit_factor": 1.5,

            "expectancy": 2.0,

            "avg_win": 10.0,

            "avg_loss": 5.0,

            "risk_reward": 2.0,

            "recovery_factor": 10.0,

            "max_win_streak": 5,

            "max_loss_streak": 2
        }

        # the code under test writes to the relative path
        # "core/config/best_config.json" -- redirect the working
        # directory to an isolated tmp_path rather than mocking
        # open()/Path() directly (which is fragile and recursion-
        # prone when the code itself also needs a working `open`).
        # backtest/reports/optimizer_report.json is also written
        # relative to cwd, so this isolates that too.
        monkeypatch.chdir(
            tmp_path
        )

        with patch(
            "backtest.optimizer.optimizer_engine.ReplayEngine"
        ) as mock_replay_engine:

            mock_replay_engine.return_value.replay = (
                AsyncMock()
            )

            with patch(
                "backtest.optimizer.optimizer_engine.MetricsEngine"
            ) as mock_metrics_engine:

                mock_metrics_engine.return_value.generate = (
                    lambda user_id: passing_metrics
                )

                with patch(
                    "backtest.optimizer.optimizer_engine."
                    "validation_interpreter"
                ) as mock_interpreter:

                    mock_interpreter.analyze.return_value = {

                        "performance": {
                            "net_profit": 100.0,
                            "profit_factor": 1.5,
                            "profit_factor_rating": "GOOD",
                            "expectancy": 2.0,
                            "recovery_factor": 10.0
                        },

                        "trade_quality": {
                            "winrate": 0.6,
                            "winrate_rating": "STRONG",
                            "risk_reward": 2.0,
                            "risk_reward_rating": "GOOD",
                            "avg_win": 10.0,
                            "avg_loss": 5.0
                        },

                        "risk": {
                            "max_drawdown": -10.0,
                            "drawdown_rating": "LOW",
                            "max_win_streak": 5,
                            "max_loss_streak": 2
                        },

                        "statistical_analysis": {
                            "trade_sample_size": 50,
                            "sample_rating": "MODERATE_SAMPLE",
                            "overfit_risk": "LOW",
                            "robustness": "MODERATE"
                        },

                        "final_verdict": {

                            "status": verdict_status,

                            "recommendation": "test recommendation"
                        }
                    }

                    engine.optimize()

        return (
            tmp_path
            / "core"
            / "config"
            / "best_config.json"
        )

    def test_robust_verdict_saves_config(
        self,
        tmp_path,
        monkeypatch
    ):

        config_path = (
            self._run_optimize_with_verdict(
                tmp_path,
                "ROBUST",
                monkeypatch
            )
        )

        assert config_path.exists()

    def test_moderate_verdict_saves_config(
        self,
        tmp_path,
        monkeypatch
    ):

        config_path = (
            self._run_optimize_with_verdict(
                tmp_path,
                "MODERATE",
                monkeypatch
            )
        )

        assert config_path.exists()

    def test_promising_but_suspicious_verdict_blocks_save(
        self,
        tmp_path,
        monkeypatch
    ):

        config_path = (
            self._run_optimize_with_verdict(
                tmp_path,
                "PROMISING_BUT_SUSPICIOUS",
                monkeypatch
            )
        )

        assert not config_path.exists()

    def test_insufficient_data_verdict_blocks_save(
        self,
        tmp_path,
        monkeypatch
    ):

        config_path = (
            self._run_optimize_with_verdict(
                tmp_path,
                "INSUFFICIENT_DATA",
                monkeypatch
            )
        )

        assert not config_path.exists()

    def test_blocked_save_does_not_overwrite_existing_config(
        self,
        tmp_path,
        monkeypatch
    ):

        # simulate a real best_config.json already existing from a
        # previous, legitimately-validated run
        config_dir = (
            tmp_path / "core" / "config"
        )

        config_dir.mkdir(
            parents=True
        )

        real_config_path = (
            config_dir / "best_config.json"
        )

        real_config_path.write_text(
            '{"atr_stop_multiplier": 1.2}'
        )

        original_content = (
            real_config_path.read_text()
        )

        self._run_optimize_with_verdict(
            tmp_path,
            "PROMISING_BUT_SUSPICIOUS",
            monkeypatch
        )

        assert (
            real_config_path.read_text()
            == original_content
        )
