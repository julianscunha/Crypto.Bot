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

        take_profit_values = [
            0.003,
            0.005,
            0.008
        ]

        stop_loss_values = [
            0.01,
            0.015,
            0.02
        ]

        combinations = []

        for tp, sl in product(
            take_profit_values,
            stop_loss_values
        ):

            combinations.append({

                "take_profit_percent": tp,

                "stop_loss_percent": sl
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
        # VALIDATION REPORT
        # =====================================================

        print()

        print("=" * 60)
        print("                 VALIDATION REPORT")
        print("=" * 60)

        print()

        performance = report["performance"]

        print("[PERFORMANCE]")

        print(
            f"Net Profit .............. "
            f"{performance['net_profit']}"
        )

        print(
            f"Profit Factor ........... "
            f"{performance['profit_factor']} "
            f"({performance['profit_factor_rating']})"
        )

        print(
            f"Expectancy .............. "
            f"{performance['expectancy']}"
        )

        print(
            f"Recovery Factor ......... "
            f"{performance['recovery_factor']}"
        )

        print()

        trade_quality = report["trade_quality"]

        print("[TRADE QUALITY]")

        print(
            f"Winrate ................. "
            f"{trade_quality['winrate']:.2%} "
            f"({trade_quality['winrate_rating']})"
        )

        print(
            f"Risk/Reward ............. "
            f"{trade_quality['risk_reward']} "
            f"({trade_quality['risk_reward_rating']})"
        )

        print(
            f"Avg Win ................. "
            f"{trade_quality['avg_win']}"
        )

        print(
            f"Avg Loss ................ "
            f"{trade_quality['avg_loss']}"
        )

        print()

        risk = report["risk"]

        print("[RISK]")

        print(
            f"Max Drawdown ............ "
            f"{risk['max_drawdown']} "
            f"({risk['drawdown_rating']})"
        )

        print(
            f"Max Win Streak .......... "
            f"{risk['max_win_streak']}"
        )

        print(
            f"Max Loss Streak ......... "
            f"{risk['max_loss_streak']}"
        )

        print()

        stats = report["statistical_analysis"]

        print("[STATISTICAL ANALYSIS]")

        print(
            f"Trade Sample Size ....... "
            f"{stats['trade_sample_size']} "
            f"({stats['sample_rating']})"
        )

        print(
            f"Overfit Risk ............ "
            f"{stats['overfit_risk']}"
        )

        print(
            f"Robustness .............. "
            f"{stats['robustness']}"
        )

        print()

        verdict = report["final_verdict"]

        print("[FINAL VERDICT]")

        print(
            f"Status .................. "
            f"{verdict['status']}"
        )

        print()

        print("Recommendation:")

        print(
            verdict["recommendation"]
        )

        print()

        print("=" * 60)

        restore_config(
            snapshot
        )


if __name__ == "__main__":

    OptimizerEngine().optimize()