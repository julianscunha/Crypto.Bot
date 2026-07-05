# -*- coding: utf-8 -*-

"""
Fetches real historical kline (candlestick) data from Binance's
public REST API, for the optimizer to train/validate against --
replacing the small, fixed synthetic datasets in backtest/datasets/.

Uses the *public*, unauthenticated /api/v3/klines endpoint -- this is
read-only market data, the same kind of public information the
existing WebSocket market feed (data/ingestion/binance_ws.py) reads,
not an authenticated trading endpoint. No API key/secret involved.

The Binance klines endpoint returns at most 1000 candles per call, so
fetching 90 days of 5m candles (~25920 per symbol) requires paginating
forward through time via startTime/endTime.
"""

import asyncio

import csv

import time

from pathlib import Path

import aiohttp

from core.utils.console_logger import (
    log
)


BINANCE_KLINES_URL = (
    "https://api.binance.com/api/v3/klines"
)

MAX_CANDLES_PER_REQUEST = 1000

# Binance's published weight limit is generous for klines requests,
# but pagination across 90 days still means dozens of sequential
# calls -- a small delay between requests keeps this well under any
# rate limit without meaningfully slowing down a one-time fetch.
REQUEST_DELAY_SECONDS = 0.25

MAX_RETRIES = 3

RETRY_BACKOFF_BASE_SECONDS = 2

INTERVAL_TO_MILLISECONDS = {

    "1m": 60_000,

    "3m": 180_000,

    "5m": 300_000,

    "15m": 900_000,

    "30m": 1_800_000,

    "1h": 3_600_000,

    "4h": 14_400_000,

    "1d": 86_400_000
}


class BinanceHistoryError(
    Exception
):

    pass


def interval_to_milliseconds(
    interval: str
) -> int:

    milliseconds = INTERVAL_TO_MILLISECONDS.get(
        interval
    )

    if milliseconds is None:

        raise BinanceHistoryError(
            f"Unsupported kline interval '{interval}'. "
            f"Supported: {', '.join(INTERVAL_TO_MILLISECONDS)}"
        )

    return milliseconds


async def _fetch_klines_page(
    session: aiohttp.ClientSession,
    symbol: str,
    interval: str,
    start_time_ms: int,
    end_time_ms: int
):

    params = {

        "symbol": symbol,

        "interval": interval,

        "startTime": start_time_ms,

        "endTime": end_time_ms,

        "limit": MAX_CANDLES_PER_REQUEST
    }

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            async with session.get(

                BINANCE_KLINES_URL,

                params=params,

                timeout=aiohttp.ClientTimeout(
                    total=15
                )

            ) as response:

                if response.status == 429:

                    # rate limited -- back off and retry rather than
                    # failing the whole fetch over a transient limit
                    retry_after = int(
                        response.headers.get(
                            "Retry-After",
                            RETRY_BACKOFF_BASE_SECONDS
                            * attempt
                        )
                    )

                    log(
                        "SYSTEM",
                        (
                            "BINANCE HISTORY RATE LIMITED "
                            f"symbol={symbol} "
                            f"retry_after={retry_after}s"
                        ),
                        "WARNING"
                    )

                    await asyncio.sleep(
                        retry_after
                    )

                    continue

                if response.status != 200:

                    body = await response.text()

                    raise BinanceHistoryError(
                        f"Binance klines request failed "
                        f"(status={response.status}): {body[:200]}"
                    )

                return await response.json()

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError
        ) as error:

            last_error = error

            backoff = (
                RETRY_BACKOFF_BASE_SECONDS
                * attempt
            )

            log(
                "SYSTEM",
                (
                    "BINANCE HISTORY REQUEST FAILED "
                    f"symbol={symbol} attempt={attempt}/{MAX_RETRIES} "
                    f"error={error} retrying_in={backoff}s"
                ),
                "WARNING"
            )

            await asyncio.sleep(
                backoff
            )

    raise BinanceHistoryError(
        f"Failed to fetch klines for {symbol} after "
        f"{MAX_RETRIES} attempts: {last_error}"
    )


async def fetch_historical_klines(
    symbol: str,
    interval: str,
    days: int
):

    """
    Returns a list of candles for `symbol`, oldest first, spanning
    approximately the last `days` days. Each candle is a dict with
    symbol/open/high/low/close/volume -- the same shape ReplayEngine
    already expects from its CSV files.
    """

    interval_ms = interval_to_milliseconds(
        interval
    )

    end_time_ms = int(
        time.time() * 1000
    )

    start_time_ms = (
        end_time_ms
        -
        (days * 24 * 60 * 60 * 1000)
    )

    candles = []

    async with aiohttp.ClientSession() as session:

        cursor_ms = start_time_ms

        while cursor_ms < end_time_ms:

            page_end_ms = min(

                cursor_ms
                +
                (
                    MAX_CANDLES_PER_REQUEST
                    *
                    interval_ms
                ),

                end_time_ms
            )

            raw_candles = await _fetch_klines_page(

                session,

                symbol,

                interval,

                cursor_ms,

                page_end_ms
            )

            if not raw_candles:

                # no more data available in this window (e.g. the
                # symbol's listing date is more recent than
                # start_time_ms) -- stop rather than loop forever
                break

            for raw in raw_candles:

                candles.append({

                    "symbol": symbol,

                    "open": float(raw[1]),

                    "high": float(raw[2]),

                    "low": float(raw[3]),

                    "close": float(raw[4]),

                    "volume": float(raw[5])
                })

            # advance the cursor past the last candle actually
            # returned (its open time + 1 interval), not just
            # page_end_ms -- Binance may return fewer candles than
            # requested near the most recent data
            last_open_time_ms = raw_candles[-1][0]

            cursor_ms = (
                last_open_time_ms
                +
                interval_ms
            )

            await asyncio.sleep(
                REQUEST_DELAY_SECONDS
            )

    return candles


def write_klines_csv(
    candles: list,
    csv_path: str
):

    """
    Writes candles (already in chronological/oldest-first order) to
    a CSV matching ReplayEngine's expected format:
    symbol,open,high,low,close,volume
    """

    path = Path(
        csv_path
    )

    path.parent.mkdir(
        parents=True,

        exist_ok=True
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(

            f,

            fieldnames=[
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        writer.writeheader()

        writer.writerows(
            candles
        )


def split_train_validation(
    candles: list,
    validation_days: int,
    interval: str
):

    """
    Splits chronologically-ordered candles into (train, validation),
    reserving the most recent `validation_days` worth of candles for
    validation and everything before that for training.

    This is a TIME split, not a random one -- shuffling candles
    before splitting would let the optimizer "validate" against data
    chronologically interleaved with what it trained on, which is
    data leakage: it would make an overfit parameter set look
    validated when it was never actually tested against unseen data.
    """

    if not candles:

        return [], []

    interval_ms = interval_to_milliseconds(
        interval
    )

    validation_candle_count = (

        (
            validation_days
            *
            24
            *
            60
            *
            60
            *
            1000
        )

        //
        interval_ms
    )

    if validation_candle_count <= 0:

        return candles, []

    if validation_candle_count >= len(candles):

        return [], candles

    split_index = (
        len(candles)
        -
        validation_candle_count
    )

    train_candles = candles[:split_index]

    validation_candles = candles[split_index:]

    return train_candles, validation_candles


async def fetch_and_save_historical_data(
    symbols: list,
    interval: str,
    days: int,
    output_dir: str
):

    """
    Fetches `days` days of history for every symbol in `symbols` and
    writes one combined, chronologically-ordered CSV per symbol to
    `output_dir`. Returns the list of CSV paths written.

    Symbols are fetched sequentially (not concurrently) -- this is a
    one-time, infrequent fetch (run once per optimizer invocation),
    not a latency-sensitive path, and sequential requests are gentler
    on Binance's public rate limits than fanning out N symbols at once.
    """

    written_paths = []

    for symbol in symbols:

        log(
            "SYSTEM",
            (
                "BINANCE HISTORY FETCHING "
                f"symbol={symbol} interval={interval} days={days}"
            )
        )

        candles = await fetch_historical_klines(
            symbol=symbol,
            interval=interval,
            days=days
        )

        csv_path = str(
            Path(output_dir) / f"{symbol.lower()}_history.csv"
        )

        write_klines_csv(
            candles,
            csv_path
        )

        log(
            "SYSTEM",
            (
                "BINANCE HISTORY SAVED "
                f"symbol={symbol} candles={len(candles)} "
                f"path={csv_path}"
            ),
            "SUCCESS"
        )

        written_paths.append(
            csv_path
        )

    return written_paths
