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

from data.storage.repositories.trades_repository import (
    trades_repository
)

from backtest.optimizer.config_runtime import (
    get_config_snapshot,
    apply_config,
    restore_config
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

    def optimize(self):

        snapshot = (
            get_config_snapshot()
        )

        combinations = (
            self.generate_combinations()
        )

        results = []

        for params in combinations:

            print()

            print(
                "[OPTIMIZER]",
                params
            )

            apply_config(
                params
            )

            trades_repository.reset()

            for dataset in self.TRAIN_DATASETS:

                replay = (
                    ReplayEngine(
                        csv_path=dataset,
                        user_id=self.USER_ID
                    )
                )

                asyncio.run(
                    replay.replay()
                )

                metrics = (
                    MetricsEngine()
                    .generate(
                        self.USER_ID
                    )
                )
                
                print(
                    "[RESULT]",
                    metrics
                )
                
                if metrics["total_trades"] < 5:
                
                    restore_config(
                        snapshot
                    )
                
                    continue
                
                # =====================================================
                # QUANT SCORE
                # =====================================================
                
                score = (
                
                    # =============================================
                    # PROFITABILITY
                    # =============================================
                
                    (
                        metrics["pnl"] * 0.30
                    )
                
                    +
                
                    # =============================================
                    # TRADE QUALITY
                    # =============================================
                
                    (
                        metrics["profit_factor"]
                        * 100
                        * 0.25
                    )
                
                    +
                
                    # =============================================
                    # EXPECTANCY
                    # =============================================
                
                    (
                        metrics["expectancy"]
                        * 10
                        * 0.20
                    )
                
                    +
                
                    # =============================================
                    # RECOVERY CAPACITY
                    # =============================================
                
                    (
                        metrics["recovery_factor"]
                        * 50
                        * 0.15
                    )
                
                    +
                
                    # =============================================
                    # RISK / REWARD
                    # =============================================
                
                    (
                        metrics["risk_reward"]
                        * 25
                        * 0.10
                    )
                
                )
                
                # =====================================================
                # DRAWDOWN PENALTY
                # =====================================================
                
                score -= (
                
                    abs(
                        metrics["max_drawdown"]
                    )
                
                    * 0.20
                )
                
                print(
                    "[SCORE]",
                    round(score, 2)
                )
            results.append({

                "params": params,

                "metrics": metrics,

                "score": round(
                    score,
                    2
                )
            })

            restore_config(
                snapshot
            )

        print()

        print(
            "[OPTIMIZER RANKING]"
        )

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

        for result in sorted_results:

            print()

            print(
                result["params"]
            )

            print(
                result["metrics"]
            )

            print(
                "Score:",
                result["score"]
            )

        # =====================================================
        # SAVE OPTIMIZER REPORT
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

        print()

        print(
            "[OPTIMIZER REPORT]",
            "backtest/reports/optimizer_report.json"
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

        print()
        
        print()

        print(
            "[WALK FORWARD VALIDATION]"
        )
        
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
        
        print()
        
        print(
            "[VALIDATION RESULT]",
            validation_metrics
        )
        
        restore_config(
            snapshot
        )
        

        print(
            "[BEST CONFIG]",
            "core/config/best_config.json"
        )


if __name__ == "__main__":

    OptimizerEngine().optimize()