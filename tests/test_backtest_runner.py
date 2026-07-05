# -*- coding: utf-8 -*-

"""
Integration test for backtest/runner.py

main() is pure sequential batch logic (no infinite loop, no network
I/O -- it replays CSV datasets and writes a JSON report), so unlike
apps/trader/runner.py's main(), it's safe to call directly in tests.
"""

import json

import os

import shutil

import pytest

from unittest.mock import patch

from backtest.runner import main as backtest_main, prepare_datasets, SYNTHETIC_DATASETS


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "backtest",
    "reports",
    "report.json"
)


@pytest.fixture(autouse=True)
def _preserve_real_report_json():

    """
    backtest/runner.py writes to a hardcoded relative path
    (backtest/reports/report.json) outside the isolated test
    database. Back it up and restore it so running this test suite
    never leaves that real artifact altered, even on failure.
    """

    backup = None

    if os.path.exists(REPORT_PATH):

        with open(REPORT_PATH, "r") as f:

            backup = f.read()

    yield

    if backup is not None:

        with open(REPORT_PATH, "w") as f:

            f.write(backup)

    elif os.path.exists(REPORT_PATH):

        os.remove(REPORT_PATH)


class TestBacktestRunnerMain:

    @pytest.mark.asyncio
    async def test_main_runs_end_to_end_without_crashing(self):

        original_cwd = os.getcwd()

        try:

            os.chdir(PROJECT_ROOT)

            await backtest_main()

        finally:

            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_main_writes_valid_report_json(self):

        original_cwd = os.getcwd()

        try:

            os.chdir(PROJECT_ROOT)

            await backtest_main()

            assert os.path.exists(REPORT_PATH)

            with open(REPORT_PATH, "r") as f:

                report = json.load(f)

            for key in (
                "total_trades",
                "winrate",
                "pnl"
            ):

                assert key in report

        finally:

            os.chdir(original_cwd)


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

    def __init__(self, candles_per_symbol=50):

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


class TestPrepareDatasets:

    """
    Bug fixed: prepare_datasets() originally called asyncio.run()
    internally, but it's invoked from within backtest/runner.py's
    main() -- itself an async function already running inside its
    own asyncio.run(main()) at the real entrypoint
    (`if __name__ == "__main__": asyncio.run(main())`). Calling
    asyncio.run() again from inside an already-running event loop
    raises "RuntimeError: asyncio.run() cannot be called from a
    running event loop", which prepare_datasets()'s own except
    Exception caught and silently swallowed -- so every real run
    fell back to the synthetic datasets without ever actually
    attempting (or even being ABLE to attempt) a real Binance fetch,
    regardless of network availability. Fixed by making
    prepare_datasets() itself async and awaiting it directly from
    main(), with no nested asyncio.run() at all.
    """

    @pytest.fixture(autouse=True)
    def _cleanup_live_history_dir(self):

        yield

        shutil.rmtree(
            os.path.join(
                PROJECT_ROOT,
                "backtest/datasets/live_history"
            ),
            ignore_errors=True
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_synthetic_on_fetch_failure(self):

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

                result = await prepare_datasets()

        assert result == SYNTHETIC_DATASETS

    @pytest.mark.asyncio
    async def test_does_not_raise_runtime_error_when_called_from_a_running_loop(
        self
    ):

        # this is the exact regression: prepare_datasets() must be
        # awaitable from within another already-running coroutine
        # (main()) without raising "asyncio.run() cannot be called
        # from a running event loop"

        async def _caller():

            return await prepare_datasets()

        # being inside this very test (itself a coroutine running
        # under pytest-asyncio's event loop) reproduces the real
        # nesting scenario -- if prepare_datasets() still called
        # asyncio.run() internally, this would raise

        result = await _caller()

        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_real_data_paths_on_successful_fetch(self):

        fake_session = _FakeSession(
            candles_per_symbol=50
        )

        original_cwd = os.getcwd()

        try:

            os.chdir(PROJECT_ROOT)

            with patch(
                "data.ingestion.binance_history."
                "aiohttp.ClientSession",
                return_value=fake_session
            ):

                result = await prepare_datasets()

            assert result != SYNTHETIC_DATASETS

            for path in result:

                assert "live_history" in path

                assert os.path.exists(path)

        finally:

            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_main_uses_real_datasets_when_fetch_succeeds(
        self
    ):

        # exercises the exact real call path: main() awaiting
        # prepare_datasets() and then replaying whatever it returns

        fake_session = _FakeSession(
            candles_per_symbol=50
        )

        original_cwd = os.getcwd()

        try:

            os.chdir(PROJECT_ROOT)

            with patch(
                "data.ingestion.binance_history."
                "aiohttp.ClientSession",
                return_value=fake_session
            ):

                await backtest_main()

            assert os.path.exists(REPORT_PATH)

        finally:

            os.chdir(original_cwd)
