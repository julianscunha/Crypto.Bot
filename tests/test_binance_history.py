# -*- coding: utf-8 -*-

"""
Unit tests for data/ingestion/binance_history.py

These mock aiohttp.ClientSession entirely -- this sandbox's network
egress blocks api.binance.com (confirmed: same restriction already
seen on the live WebSocket feed in earlier sessions), so real
connectivity can only be validated in the user's own environment
(already confirmed working there for the WebSocket feed using the
same Binance public-data convention). Every test here simulates the
exact response shapes Binance's public klines endpoint returns.
"""

import asyncio

import csv

import aiohttp

import pytest

from unittest.mock import patch

from data.ingestion.binance_history import (
    interval_to_milliseconds,
    fetch_historical_klines,
    fetch_and_save_historical_data,
    write_klines_csv,
    split_train_validation,
    BinanceHistoryError
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

    def __init__(self, responses):

        self._responses = list(responses)

        self.call_count = 0

    def get(self, url, params, timeout):

        response = (
            self._responses[self.call_count]
            if self.call_count < len(self._responses)
            else _FakeResponse([])
        )

        self.call_count += 1

        return response

    async def __aenter__(self):

        return self

    async def __aexit__(self, *args):

        return False


class TestIntervalToMilliseconds:

    def test_known_intervals(self):

        assert interval_to_milliseconds("1m") == 60_000

        assert interval_to_milliseconds("5m") == 300_000

        assert interval_to_milliseconds("1h") == 3_600_000

        assert interval_to_milliseconds("1d") == 86_400_000

    def test_unknown_interval_raises(self):

        with pytest.raises(BinanceHistoryError):

            interval_to_milliseconds("7m")


class TestFetchHistoricalKlines:

    @pytest.mark.asyncio
    async def test_single_page_returns_all_candles(self):

        interval_ms = 300_000

        page = [
            _raw_candle(i * interval_ms)
            for i in range(10)
        ]

        fake_session = _FakeSession([
            _FakeResponse(page),
            _FakeResponse([])
        ])

        with patch(
            "data.ingestion.binance_history.aiohttp.ClientSession",
            return_value=fake_session
        ):

            candles = await fetch_historical_klines(
                symbol="BTCUSDT",
                interval="5m",
                days=1
            )

        assert len(candles) == 10

        assert candles[0]["symbol"] == "BTCUSDT"

        assert candles[0]["close"] == 100.5

    @pytest.mark.asyncio
    async def test_paginates_across_multiple_pages(self):

        interval_ms = 300_000

        page1 = [
            _raw_candle(i * interval_ms)
            for i in range(1000)
        ]

        page2 = [
            _raw_candle((1000 + i) * interval_ms)
            for i in range(50)
        ]

        fake_session = _FakeSession([
            _FakeResponse(page1),
            _FakeResponse(page2),
            _FakeResponse([])
        ])

        with patch(
            "data.ingestion.binance_history.aiohttp.ClientSession",
            return_value=fake_session
        ):

            candles = await fetch_historical_klines(
                symbol="BTCUSDT",
                interval="5m",
                days=4
            )

        assert len(candles) == 1050

        assert fake_session.call_count == 3

    @pytest.mark.asyncio
    async def test_stops_on_empty_page_instead_of_looping_forever(
        self
    ):

        fake_session = _FakeSession([
            _FakeResponse([])
        ])

        with patch(
            "data.ingestion.binance_history.aiohttp.ClientSession",
            return_value=fake_session
        ):

            candles = await fetch_historical_klines(
                symbol="BTCUSDT",
                interval="5m",
                days=90
            )

        assert candles == []

        assert fake_session.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_429_rate_limit(self):

        fake_session = _FakeSession([
            _FakeResponse(
                None,
                status=429,
                headers={"Retry-After": "0"}
            ),
            _FakeResponse([
                _raw_candle(0)
            ]),
            _FakeResponse([])
        ])

        with patch(
            "data.ingestion.binance_history.aiohttp.ClientSession",
            return_value=fake_session
        ):

            candles = await fetch_historical_klines(
                symbol="BTCUSDT",
                interval="5m",
                days=1
            )

        assert len(candles) == 1

        assert fake_session.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_on_persistent_network_failure(self):

        class _AlwaysFailsSession:

            def get(self, url, params, timeout):

                raise aiohttp.ClientConnectionError(
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
                "data.ingestion.binance_history.aiohttp.ClientSession",
                return_value=_AlwaysFailsSession()
            ):

                with pytest.raises(BinanceHistoryError):

                    await fetch_historical_klines(
                        symbol="BTCUSDT",
                        interval="5m",
                        days=1
                    )

    @pytest.mark.asyncio
    async def test_raises_on_non_200_non_429_status(self):

        fake_session = _FakeSession([
            _FakeResponse(
                {"msg": "Invalid symbol"},
                status=400
            )
        ])

        with patch(
            "data.ingestion.binance_history."
            "RETRY_BACKOFF_BASE_SECONDS",
            0
        ):

            with patch(
                "data.ingestion.binance_history.aiohttp.ClientSession",
                return_value=fake_session
            ):

                with pytest.raises(BinanceHistoryError):

                    await fetch_historical_klines(
                        symbol="NOTREAL",
                        interval="5m",
                        days=1
                    )


class TestWriteKlinesCsv:

    def test_writes_expected_header_and_rows(self, tmp_path):

        candles = [
            {
                "symbol": "BTCUSDT",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 10.0
            },
            {
                "symbol": "BTCUSDT",
                "open": 100.5,
                "high": 102.0,
                "low": 100.0,
                "close": 101.5,
                "volume": 12.0
            }
        ]

        csv_path = str(
            tmp_path / "history.csv"
        )

        write_klines_csv(
            candles,
            csv_path
        )

        with open(csv_path) as f:

            reader = csv.DictReader(f)

            rows = list(reader)

            assert reader.fieldnames == [
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]

        assert len(rows) == 2

        assert rows[0]["symbol"] == "BTCUSDT"

    def test_creates_parent_directory_if_missing(self, tmp_path):

        nested_path = str(
            tmp_path / "nested" / "dir" / "history.csv"
        )

        write_klines_csv(
            [{
                "symbol": "BTCUSDT",
                "open": 1,
                "high": 1,
                "low": 1,
                "close": 1,
                "volume": 1
            }],
            nested_path
        )

        from pathlib import Path

        assert Path(nested_path).exists()

    def test_output_is_readable_by_replay_engine(self, tmp_path):

        from backtest.engine.replay_engine import ReplayEngine

        candles = [
            {
                "symbol": "BTCUSDT",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 10.0
            }
        ]

        csv_path = str(
            tmp_path / "history.csv"
        )

        write_klines_csv(
            candles,
            csv_path
        )

        engine = ReplayEngine(
            csv_path=csv_path,
            user_id=9999991
        )

        asyncio.run(
            engine.replay()
        )


class TestFetchAndSaveHistoricalData:

    @pytest.mark.asyncio
    async def test_writes_one_csv_per_symbol(self, tmp_path):

        fake_session = _FakeSession([

            _FakeResponse([
                _raw_candle(0)
            ]),

            _FakeResponse([]),

            _FakeResponse([
                _raw_candle(0)
            ]),

            _FakeResponse([])
        ])

        with patch(
            "data.ingestion.binance_history.aiohttp.ClientSession",
            return_value=fake_session
        ):

            paths = await fetch_and_save_historical_data(
                symbols=["BTCUSDT", "ETHUSDT"],
                interval="5m",
                days=1,
                output_dir=str(tmp_path)
            )

        assert len(paths) == 2

        for path in paths:

            from pathlib import Path

            assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_csv_filenames_are_lowercase_symbol_based(
        self,
        tmp_path
    ):

        fake_session = _FakeSession([

            _FakeResponse([
                _raw_candle(0)
            ]),

            _FakeResponse([])
        ])

        with patch(
            "data.ingestion.binance_history.aiohttp.ClientSession",
            return_value=fake_session
        ):

            paths = await fetch_and_save_historical_data(
                symbols=["BTCUSDT"],
                interval="5m",
                days=1,
                output_dir=str(tmp_path)
            )

        assert paths[0].endswith(
            "btcusdt_history.csv"
        )


class TestSplitTrainValidation:

    def test_splits_chronologically_without_overlap(self):

        candles = [
            {"i": i}
            for i in range(25_920)
        ]

        train, validation = split_train_validation(
            candles,
            validation_days=15,
            interval="5m"
        )

        assert len(train) + len(validation) == len(candles)

        assert train[-1]["i"] < validation[0]["i"]

    def test_validation_is_the_most_recent_data(self):

        candles = [
            {"i": i}
            for i in range(100)
        ]

        _, validation = split_train_validation(
            candles,
            validation_days=1,
            interval="1d"
        )

        assert validation[-1]["i"] == 99

    def test_does_not_shuffle_train_data(self):

        candles = [
            {"i": i}
            for i in range(100)
        ]

        train, _ = split_train_validation(
            candles,
            validation_days=1,
            interval="1d"
        )

        assert [c["i"] for c in train] == list(
            range(len(train))
        )

    def test_empty_candles_returns_empty_splits(self):

        train, validation = split_train_validation(
            [],
            validation_days=15,
            interval="5m"
        )

        assert train == []

        assert validation == []

    def test_validation_days_exceeding_available_data(self):

        candles = [
            {"i": i}
            for i in range(10)
        ]

        train, validation = split_train_validation(
            candles,
            validation_days=90,
            interval="1d"
        )

        assert train == []

        assert len(validation) == 10

    def test_zero_validation_days_keeps_everything_in_train(self):

        candles = [
            {"i": i}
            for i in range(10)
        ]

        train, validation = split_train_validation(
            candles,
            validation_days=0,
            interval="1d"
        )

        assert len(train) == 10

        assert validation == []
