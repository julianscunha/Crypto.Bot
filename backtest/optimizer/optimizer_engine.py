# -*- coding: utf-8 -*-

import asyncio
import json

from itertools import product

from pathlib import Path

from backtest.engine.replay_engine import (
    ReplayEngine
)

from backtest.engine.metrics_engine import (
    MetricsEngine
)

from backtest.reports.validation_interpreter import (
    validation_interpreter
)

from backtest.reports.report_renderer import (
    ReportRenderer
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from backtest.optimizer.config_runtime import (
    get_config_snapshot,
    apply_config,
    restore_config
)

from core.utils.console_logger import (
    log
)


class OptimizerEngine:

    TRAIN_DATASETS = [

        "backtest/datasets/bullish.csv",

        "backtest/datasets/bearish.csv",

        "backtest/datasets/sideways.csv",

        "backtest/datasets/volatile.csv"
    ]

    VALIDATION_DATASET = (
        "backtest/datasets/validation.csv"
    )

    USER_ID = 999

    # =====================================================
    # COMBINATIONS
    # =====================================================

    def generate_combinations(self):

        atr_take_profit_values = [
            2.0,
            3.0,
            4.0
        ]
        
        atr_stop_values = [
            1.0,
            1.5,
            2.0
        ]
        
        atr_trailing_values = [
            0.5,
            1.0,
            1.5
        ]

        combinations = []

        for tp, sl, trailing in product(
            atr_take_profit_values,
            atr_stop_values,
            atr_trailing_values
        ):

            combinations.append({
            
                "atr_take_profit_multiplier": tp,
            
                "atr_stop_multiplier": sl,
            
                "atr_trailing_multiplier": trailing
            })

        return combinations

    # =====================================================
    # OPTIMIZER
    # =====================================================

    def optimize(self):

        print()

        print("=" * 60)
        print("                 OPTIMIZATION ENGINE")
        print("=" * 60)

        snapshot = (
            get_config_snapshot()
        )

        combinations = (
            self.generate_combinations()
        )

        results = []

        # =====================================================
        # ITERATIONS
        # =====================================================

        for index, params in enumerate(
            combinations,
            start=1
        ):

            print()

            print("=" * 60)

            log(
                "OPTIMIZER",
                (
                    f"TEST {index}/{len(combinations)} "
                    f"{params}"
                )
            )

            apply_config(
                params
            )

            trades_repository.reset()

            # =================================================
            # TRAIN DATASETS
            # =================================================

            for dataset in self.TRAIN_DATASETS:

                log(
                    "DATASET",
                    dataset
                )

                replay = (
                    ReplayEngine(
                        csv_path=dataset,
                        user_id=self.USER_ID
                    )
                )

                asyncio.run(
                    replay.replay()
                )

            # =================================================
            # METRICS
            # =================================================

            metrics = (
                MetricsEngine()
                .generate(
                    self.USER_ID
                )
            )

            # =================================================
            # VALIDATION
            # =================================================

            if metrics["total_trades"] < 5:

                log(
                    "OPTIMIZER",
                    "SKIPPED LOW_SAMPLE",
                    "WARNING"
                )

                restore_config(
                    snapshot
                )

                continue

            # =================================================
            # SCORE
            # =================================================

            score = (

                (
                    metrics["pnl"] * 0.30
                )

                +

                (
                    metrics["profit_factor"]
                    * 100
                    * 0.25
                )

                +

                (
                    metrics["expectancy"]
                    * 10
                    * 0.20
                )

                +

                (
                    metrics["recovery_factor"]
                    * 50
                    * 0.15
                )

                +

                (
                    metrics["risk_reward"]
                    * 25
                    * 0.10
                )
            )

            score -= (

                abs(
                    metrics["max_drawdown"]
                )

                * 0.20
            )

            score = round(
                score,
                2
            )

            # =================================================
            # RESULT
            # =================================================

            log(
                "RESULT",
                (
                    f"PNL={metrics['pnl']} "
                    f"PF={metrics['profit_factor']} "
                    f"WR={metrics['winrate']:.2%} "
                    f"SCORE={score}"
                ),
                "SUCCESS"
            )

            results.append({

                "params": params,

                "metrics": metrics,

                "score": score
            })

            restore_config(
                snapshot
            )

        # =====================================================
        # RANKING
        # =====================================================

        print()

        print("=" * 60)
        print("                 OPTIMIZER RANKING")
        print("=" * 60)

        sorted_results = sorted(

            results,

            key=lambda x: (
                x["score"]
            ),

            reverse=True
        )

        best_result = (
            sorted_results[0]
        )

        for index, result in enumerate(
            sorted_results,
            start=1
        ):

            print()

            log(
                "RANK",
                (
                    f"#{index} "
                    f"SCORE={result['score']} "
                    f"PF={result['metrics']['profit_factor']} "
                    f"WR={result['metrics']['winrate']:.2%}"
                )
            )

            print(
                result["params"]
            )

        # =====================================================
        # SAVE REPORT
        # =====================================================

        Path(
            "backtest/reports"
        ).mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            "backtest/reports/optimizer_report.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                sorted_results,
                f,
                indent=4
            )

        log(
            "SYSTEM",
            (
                "REPORT "
                "backtest/reports/optimizer_report.json"
            )
        )

        # =====================================================
        # SAVE BEST CONFIG
        # =====================================================

        Path(
            "core/config"
        ).mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            "core/config/best_config.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                best_result,
                f,
                indent=4
            )

        log(
            "SYSTEM",
            (
                "BEST CONFIG "
                "core/config/best_config.json"
            ),
            "SUCCESS"
        )

        # =====================================================
        # WALK FORWARD VALIDATION
        # =====================================================

        print()

        print("=" * 60)
        print("              WALK FORWARD VALIDATION")
        print("=" * 60)

        apply_config(
            best_result["params"]
        )

        trades_repository.reset()

        validation_replay = (
            ReplayEngine(
                csv_path=self.VALIDATION_DATASET,
                user_id=self.USER_ID
            )
        )

        asyncio.run(
            validation_replay.replay()
        )

        validation_metrics = (
            MetricsEngine()
            .generate(
                self.USER_ID
            )
        )

        report = (
            validation_interpreter.analyze(
                validation_metrics
            )
        )

        # =====================================================
        # OPTIMIZER VALIDATION REPORT
        # =====================================================

        performance = report["performance"]

        trade_quality = report["trade_quality"]

        risk = report["risk"]

        stats = report["statistical_analysis"]

        verdict = report["final_verdict"]

        ReportRenderer.print_header(
            "OPTIMIZER VALIDATION REPORT"
        )

        # =====================================================
        # PERFORMANCE
        # =====================================================

        ReportRenderer.print_section(
            "PERFORMANCE"
        )

        ReportRenderer.print_metric(
            "Net Profit",
            performance["net_profit"]
        )

        ReportRenderer.print_metric(
            "Profit Factor",
            performance["profit_factor"],
            performance["profit_factor_rating"]
        )

        ReportRenderer.print_metric(
            "Expectancy",
            performance["expectancy"]
        )

        ReportRenderer.print_metric(
            "Recovery Factor",
            performance["recovery_factor"]
        )

        # =====================================================
        # TRADE QUALITY
        # =====================================================

        ReportRenderer.print_section(
            "TRADE QUALITY"
        )

        ReportRenderer.print_metric(
            "Winrate",
            f"{trade_quality['winrate']:.2%}",
            trade_quality["winrate_rating"]
        )

        ReportRenderer.print_metric(
            "Risk/Reward",
            trade_quality["risk_reward"],
            trade_quality["risk_reward_rating"]
        )

        ReportRenderer.print_metric(
            "Avg Win",
            trade_quality["avg_win"]
        )

        ReportRenderer.print_metric(
            "Avg Loss",
            trade_quality["avg_loss"]
        )

        # =====================================================
        # RISK
        # =====================================================

        ReportRenderer.print_section(
            "RISK"
        )

        ReportRenderer.print_metric(
            "Max Drawdown",
            risk["max_drawdown"],
            risk["drawdown_rating"]
        )

        ReportRenderer.print_metric(
            "Max Win Streak",
            risk["max_win_streak"]
        )

        ReportRenderer.print_metric(
            "Max Loss Streak",
            risk["max_loss_streak"]
        )

        # =====================================================
        # STATISTICAL ANALYSIS
        # =====================================================

        ReportRenderer.print_section(
            "STATISTICAL ANALYSIS"
        )

        ReportRenderer.print_metric(
            "Trade Sample Size",
            stats["trade_sample_size"],
            stats["sample_rating"]
        )

        ReportRenderer.print_metric(
            "Overfit Risk",
            stats["overfit_risk"]
        )

        ReportRenderer.print_metric(
            "Robustness",
            stats["robustness"]
        )

        # =====================================================
        # FINAL VERDICT
        # =====================================================

        ReportRenderer.print_verdict(
            verdict["status"],
            verdict["recommendation"]
        )

        # =====================================================
        # OPTIMIZATION SUMMARY
        # =====================================================

        ReportRenderer.print_header(
            "TRAINING SUMMARY"
        )

        ReportRenderer.print_metric(
            "Configurations Tested",
            len(combinations)
        )

        ReportRenderer.print_metric(
            "Valid Results",
            len(sorted_results)
        )

        ReportRenderer.print_metric(
            "Training Score",
            best_result["score"]
        )

        ReportRenderer.print_metric(
            "Training Profit Factor",
            best_result["metrics"]["profit_factor"]
        )

        ReportRenderer.print_metric(
            "Training Winrate",
            f"{best_result['metrics']['winrate']:.2%}"
        )

        # =====================================================
        # CONFIG EXPORT
        # =====================================================

        ReportRenderer.print_header(
            "CONFIG EXPORT"
        )

        ReportRenderer.print_metric(
            "Generated File",
            "core/config/best_config.json"
        )

        ReportRenderer.print_metric(
            "Export Status",
            "SUCCESS"
        )

        ReportRenderer.print_footer()

        restore_config(
            snapshot
        )

if __name__ == "__main__":

    OptimizerEngine().optimize()