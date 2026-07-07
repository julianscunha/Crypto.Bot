# -*- coding: utf-8 -*-

from __future__ import annotations

import ctypes
import os
import statistics
from collections.abc import Iterable

from data.ingestion.binance_history import interval_to_milliseconds


BASE_CPU_COUNT = 4.0
BASE_MEMORY_GB = 8.0

DEFAULT_SECONDS_PER_UNIT = {
    "optimizer": 0.010,
    "backtest": 0.006,
}


def _get_total_memory_gb() -> float | None:

    try:

        if os.name == "nt":

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

            if ctypes.windll.kernel32.GlobalMemoryStatusEx(
                ctypes.byref(status)
            ):

                return round(
                    status.ullTotalPhys / (1024 ** 3),
                    2
                )

        meminfo = "/proc/meminfo"

        if os.path.exists(meminfo):

            with open(meminfo, encoding="utf-8") as file:

                for line in file:

                    if line.startswith("MemTotal:"):

                        parts = line.split()
                        if len(parts) >= 2:
                            return round(
                                int(parts[1]) / (1024 ** 2),
                                2
                            )

    except Exception:

        pass

    return None


def get_system_profile() -> dict:

    cpu_count = max(int(os.cpu_count() or 1), 1)
    memory_gb = _get_total_memory_gb()

    if memory_gb is None:

        memory_gb = BASE_MEMORY_GB

    cpu_factor = max(cpu_count / BASE_CPU_COUNT, 0.5)
    memory_factor = max(memory_gb / BASE_MEMORY_GB, 0.75)

    # CPU tends to dominate replay work, memory acts as a dampener
    # when the machine is constrained.
    capacity_score = round(
        (cpu_factor * 0.75) + (memory_factor * 0.25),
        3
    )

    return {
        "cpu_count": cpu_count,
        "memory_gb": memory_gb,
        "cpu_factor": round(cpu_factor, 3),
        "memory_factor": round(memory_factor, 3),
        "capacity_score": capacity_score,
    }


def count_optimizer_combinations(minimum_rr: float) -> int:

    tp_values = [2.0, 3.0, 4.0]
    sl_values = [1.0, 1.5, 2.0]
    trailing_values = [0.5, 1.0, 1.5]

    total = 0

    for tp in tp_values:
        for sl in sl_values:
            if (tp / sl) < minimum_rr:
                continue
            for _ in trailing_values:
                total += 1

    return total


def _parse_job_days(job_type: str, extra_args: Iterable[str] | None) -> int:

    if job_type != "optimizer":
        return 90

    args = list(extra_args or [])

    if "--days" in args:

        try:

            return max(int(args[args.index("--days") + 1]), 1)

        except Exception:

            return 90

    return 90


def build_job_profile(
    job_type: str,
    days: int,
    symbols: Iterable[str],
    interval: str,
    minimum_rr: float,
) -> dict:

    symbols_list = list(symbols)
    symbol_count = max(len(symbols_list), 1)
    interval_ms = interval_to_milliseconds(interval)
    candles_per_symbol = max(
        1,
        round((days * 24 * 60 * 60 * 1000) / interval_ms)
    )

    if job_type == "optimizer":

        combinations = count_optimizer_combinations(minimum_rr)
        units = symbol_count * candles_per_symbol * combinations

    else:

        combinations = 1
        units = symbol_count * candles_per_symbol

    return {
        "job_type": job_type,
        "days": days,
        "symbol_count": symbol_count,
        "interval": interval,
        "interval_ms": interval_ms,
        "candles_per_symbol": candles_per_symbol,
        "dataset_count": symbol_count,
        "combination_count": combinations,
        "work_units": max(units, 1),
    }


def _reference_seconds_per_unit(sample: dict) -> float | None:

    workload = sample.get("workload") or {}
    units = int(workload.get("work_units") or 0)

    if units <= 0:
        return None

    hardware = workload.get("hardware") or {}
    capacity_score = float(hardware.get("capacity_score") or 0)

    if capacity_score <= 0:
        capacity_score = 1.0

    elapsed = float(sample.get("elapsed_seconds") or 0)

    if elapsed <= 0:
        return None

    return (elapsed * capacity_score) / units


def estimate_job_duration_seconds(
    job_type: str,
    days: int,
    symbols: Iterable[str],
    interval: str,
    minimum_rr: float,
    history: Iterable[dict] | None = None,
) -> dict:

    profile = build_job_profile(
        job_type=job_type,
        days=days,
        symbols=symbols,
        interval=interval,
        minimum_rr=minimum_rr,
    )
    hardware = get_system_profile()

    samples = [
        sample
        for sample in (history or [])
        if sample.get("type") == job_type
        and sample.get("status") == "done"
        and sample.get("elapsed_seconds")
    ]

    per_unit_samples = [
        value
        for value in (
            _reference_seconds_per_unit(sample)
            for sample in samples
        )
        if value is not None
    ]

    if per_unit_samples:

        baseline_seconds_per_unit = statistics.median(
            per_unit_samples
        )

        basis = "history"

    else:

        baseline_seconds_per_unit = DEFAULT_SECONDS_PER_UNIT.get(
            job_type,
            DEFAULT_SECONDS_PER_UNIT["optimizer"]
        )

        basis = "heuristic"

    estimate_seconds = round(
        baseline_seconds_per_unit
        * profile["work_units"]
        / hardware["capacity_score"]
    )

    estimate_seconds = max(1, int(estimate_seconds))

    return {
        "estimate_seconds": estimate_seconds,
        "basis": basis,
        "profile": profile,
        "hardware": hardware,
        "sample_count": len(per_unit_samples),
    }


def parse_days_from_extra_args(extra_args: Iterable[str] | None) -> int:

    return _parse_job_days("optimizer", extra_args)
