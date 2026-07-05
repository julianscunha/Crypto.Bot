# -*- coding: utf-8 -*-

"""
Unit tests for backtest/reports/validation_interpreter.py

All winrate values here are 0-1 fractions, matching the unit
convention enforced by data/storage/metrics.py and used consistently
across optimizer_engine.py / backtest/runner.py.
"""

from backtest.reports.validation_interpreter import (
    ValidationInterpreter
)


class TestClassifyWinrate:

    def test_low(self):

        interpreter = ValidationInterpreter()

        assert interpreter._classify_winrate(0.30) == "LOW"

    def test_normal(self):

        interpreter = ValidationInterpreter()

        assert interpreter._classify_winrate(0.50) == "NORMAL"

    def test_strong(self):

        interpreter = ValidationInterpreter()

        assert interpreter._classify_winrate(0.65) == "STRONG"

    def test_extremely_high(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_winrate(0.90)
            == "EXTREMELY_HIGH"
        )

    def test_boundary_at_0_40(self):

        interpreter = ValidationInterpreter()

        assert interpreter._classify_winrate(0.40) == "NORMAL"

    def test_boundary_at_0_60(self):

        interpreter = ValidationInterpreter()

        assert interpreter._classify_winrate(0.60) == "STRONG"

    def test_boundary_at_0_75(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_winrate(0.75)
            == "EXTREMELY_HIGH"
        )


class TestClassifyProfitFactor:

    def test_losing(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_profit_factor(0.8)
            == "LOSING"
        )

    def test_weak(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_profit_factor(1.2)
            == "WEAK"
        )

    def test_good(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_profit_factor(1.7)
            == "GOOD"
        )

    def test_excellent(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_profit_factor(2.5)
            == "EXCELLENT"
        )

    def test_suspicious(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_profit_factor(4.0)
            == "SUSPICIOUS"
        )


class TestClassifyDrawdown:

    def test_critical_when_pnl_non_positive(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_drawdown(
                pnl=-10,
                drawdown=5
            )
            == "CRITICAL"
        )

        assert (
            interpreter._classify_drawdown(
                pnl=0,
                drawdown=5
            )
            == "CRITICAL"
        )

    def test_high_when_ratio_above_50_percent(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_drawdown(
                pnl=100,
                drawdown=60
            )
            == "HIGH"
        )

    def test_moderate(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_drawdown(
                pnl=100,
                drawdown=35
            )
            == "MODERATE"
        )

    def test_low(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_drawdown(
                pnl=100,
                drawdown=20
            )
            == "LOW"
        )

    def test_very_low(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_drawdown(
                pnl=100,
                drawdown=5
            )
            == "VERY_LOW"
        )


class TestClassifySampleSize:

    def test_low_sample(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_sample_size(50)
            == "LOW_SAMPLE"
        )

    def test_moderate_sample(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_sample_size(200)
            == "MODERATE_SAMPLE"
        )

    def test_statistically_relevant(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_sample_size(500)
            == "STATISTICALLY_RELEVANT"
        )


class TestClassifyRiskReward:

    def test_poor(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_risk_reward(0.5)
            == "POOR"
        )

    def test_average(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_risk_reward(1.2)
            == "AVERAGE"
        )

    def test_good(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_risk_reward(1.7)
            == "GOOD"
        )

    def test_excellent(self):

        interpreter = ValidationInterpreter()

        assert (
            interpreter._classify_risk_reward(2.5)
            == "EXCELLENT"
        )


class TestDetectOverfit:

    def test_high_overfit_risk(self):

        interpreter = ValidationInterpreter()

        result = interpreter._detect_overfit(
            winrate=0.85,
            profit_factor=6.0,
            pnl=1000,
            drawdown=10,
            trades=50
        )

        assert result == "HIGH"

    def test_moderate_overfit_risk(self):

        interpreter = ValidationInterpreter()

        result = interpreter._detect_overfit(
            winrate=0.75,
            profit_factor=3.5,
            pnl=1000,
            drawdown=200,
            trades=150
        )

        assert result == "MODERATE"

    def test_low_overfit_risk_with_realistic_stats(self):

        interpreter = ValidationInterpreter()

        result = interpreter._detect_overfit(
            winrate=0.55,
            profit_factor=1.6,
            pnl=500,
            drawdown=150,
            trades=200
        )

        assert result == "LOW"

    def test_high_overfit_requires_low_trade_count(self):

        interpreter = ValidationInterpreter()

        # same suspicious ratios but large sample -> not HIGH anymore
        result = interpreter._detect_overfit(
            winrate=0.85,
            profit_factor=6.0,
            pnl=1000,
            drawdown=10,
            trades=500
        )

        assert result != "HIGH"


class TestCalculateRobustness:

    def test_institutional_with_all_criteria_met(self):

        interpreter = ValidationInterpreter()

        result = interpreter._calculate_robustness(
            winrate=0.60,
            profit_factor=2.0,
            drawdown=1000,
            trades=150
        )

        assert result == "INSTITUTIONAL"

    def test_strong_with_three_criteria(self):

        interpreter = ValidationInterpreter()

        result = interpreter._calculate_robustness(
            winrate=0.60,
            profit_factor=2.0,
            drawdown=1000,
            trades=50
        )

        assert result == "STRONG"

    def test_weak_with_no_criteria_met(self):

        interpreter = ValidationInterpreter()

        result = interpreter._calculate_robustness(
            winrate=0.30,
            profit_factor=0.8,
            drawdown=10000,
            trades=10
        )

        assert result == "WEAK"

    def test_moderate_with_two_criteria(self):

        interpreter = ValidationInterpreter()

        result = interpreter._calculate_robustness(
            winrate=0.60,
            profit_factor=2.0,
            drawdown=10000,
            trades=10
        )

        assert result == "MODERATE"


class TestGenerateVerdict:

    def test_promising_but_suspicious_when_overfit_high(self):

        interpreter = ValidationInterpreter()

        verdict = interpreter._generate_verdict(
            overfit_risk="HIGH",
            robustness="STRONG",
            sample_rating="STATISTICALLY_RELEVANT"
        )

        assert verdict["status"] == "PROMISING_BUT_SUSPICIOUS"

    def test_robust_when_robustness_strong(self):

        interpreter = ValidationInterpreter()

        verdict = interpreter._generate_verdict(
            overfit_risk="LOW",
            robustness="STRONG",
            sample_rating="MODERATE_SAMPLE"
        )

        assert verdict["status"] == "ROBUST"

    def test_insufficient_data_when_low_sample(self):

        interpreter = ValidationInterpreter()

        verdict = interpreter._generate_verdict(
            overfit_risk="LOW",
            robustness="WEAK",
            sample_rating="LOW_SAMPLE"
        )

        assert verdict["status"] == "INSUFFICIENT_DATA"

    def test_moderate_fallback(self):

        interpreter = ValidationInterpreter()

        verdict = interpreter._generate_verdict(
            overfit_risk="LOW",
            robustness="MODERATE",
            sample_rating="MODERATE_SAMPLE"
        )

        assert verdict["status"] == "MODERATE"


class TestAnalyzeFullReport:

    def test_returns_all_required_sections(self):

        interpreter = ValidationInterpreter()

        metrics = {
            "total_trades": 150,
            "winrate": 0.58,
            "pnl": 1200.0,
            "max_drawdown": 300.0,
            "profit_factor": 1.8,
            "expectancy": 8.0,
            "avg_win": 50.0,
            "avg_loss": -25.0,
            "risk_reward": 2.0,
            "recovery_factor": 4.0,
            "max_win_streak": 6,
            "max_loss_streak": 3
        }

        report = interpreter.analyze(metrics)

        for section in (
            "performance",
            "trade_quality",
            "risk",
            "statistical_analysis",
            "final_verdict"
        ):

            assert section in report

        assert report["trade_quality"]["winrate"] == 0.58

        assert report["risk"]["max_drawdown"] == 300.0

    def test_handles_missing_keys_with_defaults(self):

        interpreter = ValidationInterpreter()

        report = interpreter.analyze({})

        assert report["statistical_analysis"][
            "trade_sample_size"
        ] == 0

        assert report["trade_quality"]["winrate"] == 0

    def test_negative_drawdown_is_normalized_to_positive(self):

        interpreter = ValidationInterpreter()

        metrics = {
            "total_trades": 10,
            "winrate": 0.5,
            "pnl": 100.0,
            "max_drawdown": -50.0,
            "profit_factor": 1.5,
            "risk_reward": 1.2
        }

        report = interpreter.analyze(metrics)

        assert report["risk"]["max_drawdown"] == 50.0
