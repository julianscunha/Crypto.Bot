# -*- coding: utf-8 -*-

import asyncio

from itertools import product

from backtest.engine.replay_engine import (
    ReplayEngine
)

from backtest.engine.metrics_engine import (
    MetricsEngine
)

import json

from pathlib import Path

from data.storage.repositories.trades_repository import (
    trades_repository
)

from backtest.optimizer.config_runtime import (
    get_config_snapshot,
    apply_config,
    restore_config
)


class OptimizerEngine:

    DATASETS = [

        "backtest/datasets/bullish.csv",

        "backtest/datasets/bearish.csv",

        "backtest/datasets/sideways.csv",

        "backtest/datasets/volatile.csv"
    ]

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

            for dataset in self.DATASETS:

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
                continue
            
            score = (
            
                metrics["pnl"]
            
                *
            
                metrics["winrate"]
            
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
        
        print()
        
        print(
            "[OPTIMIZER REPORT]",
            "backtest/reports/optimizer_report.json"
        )


if __name__ == "__main__":

    OptimizerEngine().optimize()