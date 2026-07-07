# -*- coding: utf-8 -*-

from core.services.job_estimation_service import (
    build_job_profile,
    count_optimizer_combinations,
    estimate_job_duration_seconds,
)

import core.services.job_estimation_service as job_estimation_service


class TestBuildJobProfile:

    def test_optimizer_profile_uses_days_symbols_and_combinations(self):

        profile = build_job_profile(
            job_type="optimizer",
            days=90,
            symbols=["BTCUSDT", "ETHUSDT"],
            interval="1h",
            minimum_rr=1.5,
        )

        assert profile["symbol_count"] == 2
        assert profile["candles_per_symbol"] == 2160
        assert profile["combination_count"] == count_optimizer_combinations(1.5)
        assert profile["work_units"] == 2 * 2160 * profile["combination_count"]

    def test_backtest_profile_has_one_combination_per_symbol(self):

        profile = build_job_profile(
            job_type="backtest",
            days=90,
            symbols=["BTCUSDT", "ETHUSDT", "XRPUSDT"],
            interval="15m",
            minimum_rr=1.5,
        )

        assert profile["symbol_count"] == 3
        assert profile["combination_count"] == 1
        assert profile["work_units"] == 3 * profile["candles_per_symbol"]


class TestEstimateJobDurationSeconds:

    def test_history_calibration_is_adjusted_by_current_hardware(self, monkeypatch):

        monkeypatch.setattr(
            job_estimation_service,
            "get_system_profile",
            lambda: {
                "cpu_count": 8,
                "memory_gb": 16.0,
                "cpu_factor": 2.0,
                "memory_factor": 2.0,
                "capacity_score": 2.0,
            },
        )

        history = [
            {
                "type": "backtest",
                "status": "done",
                "elapsed_seconds": 120,
                "workload": {
                    "work_units": 24,
                    "hardware": {
                        "capacity_score": 1.0,
                    },
                },
            }
        ]

        estimate = estimate_job_duration_seconds(
            job_type="backtest",
            days=1,
            symbols=["BTCUSDT"],
            interval="1h",
            minimum_rr=1.5,
            history=history,
        )

        assert estimate["basis"] == "history"
        assert estimate["estimate_seconds"] == 60

    def test_falls_back_to_heuristic_without_history(self, monkeypatch):

        monkeypatch.setattr(
            job_estimation_service,
            "get_system_profile",
            lambda: {
                "cpu_count": 4,
                "memory_gb": 8.0,
                "cpu_factor": 1.0,
                "memory_factor": 1.0,
                "capacity_score": 1.0,
            },
        )

        estimate = estimate_job_duration_seconds(
            job_type="optimizer",
            days=30,
            symbols=["BTCUSDT"],
            interval="1h",
            minimum_rr=1.5,
            history=[],
        )

        assert estimate["basis"] == "heuristic"
        assert estimate["estimate_seconds"] > 0
