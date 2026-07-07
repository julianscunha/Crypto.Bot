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

from backtest.reports.progress_writer import (
    write_progress,
    clear_progress
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

from core.services.market_structure_service import (
    market_structure_service
)

from core.config.settings import (
    settings
)

from data.ingestion.binance_history import (
    fetch_historical_klines,
    split_train_validation,
    write_klines_csv,
    BinanceHistoryError
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
    # REAL HISTORICAL DATA
    # =====================================================
    #
    # How much real market history to fetch from Binance before
    # every optimization run, and how much of the most recent slice
    # to hold back as validation data (chronological split, never
    # shuffled -- see data/ingestion/binance_history.py
    # split_train_validation() for why a random split would leak
    # information from validation back into training).

    HISTORY_DAYS = 90

    VALIDATION_DAYS = 15

    HISTORY_OUTPUT_DIR = (
        "backtest/datasets/live_history"
    )

    # =====================================================
    # VALIDATION GATE
    # =====================================================
    #
    # Verdicts from backtest/reports/validation_interpreter.py that
    # must block best_config.json from being saved/overwritten.
    # Previously the file was saved unconditionally BEFORE
    # walk-forward validation even ran, so a config that the
    # optimizer's own validation report called out as overfit
    # (PROMISING_BUT_SUSPICIOUS) or backed by too little data
    # (INSUFFICIENT_DATA) was still picked up by
    # core/config/config_loader.py on the Runner's next start --
    # exactly as if it had passed validation cleanly.

    BLOCKING_VERDICTS = (
        "PROMISING_BUT_SUSPICIOUS",

        "INSUFFICIENT_DATA"
    )

    def __init__(self, history_days: int = None):

        if history_days is not None:
            self.HISTORY_DAYS = history_days

        self._prepare_datasets()

    # =====================================================
    # DATASET PREPARATION
    # =====================================================
    #
    # Replaces the small, fixed synthetic CSVs above with real
    # market history fetched fresh from Binance's public klines
    # endpoint every time the optimizer runs -- the optimizer was
    # previously tuning parameters against the same ~20-candle
    # example datasets every single run, regardless of how the
    # actual market had moved since. Falls back to the synthetic
    # datasets (with a clear warning) if the fetch fails for any
    # reason -- a network hiccup must never block the user from
    # running an optimization at all, it should just visibly use
    # weaker data.

    def _prepare_datasets(self):

        try:

            asyncio.run(
                self._fetch_real_datasets()
            )

        except Exception as error:

            log(
                "SYSTEM",
                (
                    "OPTIMIZER REAL DATA FETCH FAILED "
                    f"{error} -- falling back to synthetic "
                    "example datasets in backtest/datasets/"
                ),
                "WARNING"
            )

    async def _fetch_real_datasets(self):

        symbols = (
            settings.SYMBOLS
        )

        interval = (
            settings.KLINE_INTERVAL
        )

        log(
            "SYSTEM",
            (
                "OPTIMIZER FETCHING REAL HISTORY "
                f"symbols={symbols} interval={interval} "
                f"days={self.HISTORY_DAYS}"
            )
        )

        train_paths = []

        validation_paths = []

        for symbol in symbols:

            candles = await fetch_historical_klines(
                symbol=symbol,
                interval=interval,
                days=self.HISTORY_DAYS
            )

            if not candles:

                raise BinanceHistoryError(
                    f"No historical candles returned for {symbol}"
                )

            train_candles, validation_candles = (

                split_train_validation(
                    candles,
                    validation_days=self.VALIDATION_DAYS,
                    interval=interval
                )
            )

            train_path = (
                f"{self.HISTORY_OUTPUT_DIR}/"
                f"{symbol.lower()}_train.csv"
            )

            validation_path = (
                f"{self.HISTORY_OUTPUT_DIR}/"
                f"{symbol.lower()}_validation.csv"
            )

            write_klines_csv(
                train_candles,
                train_path
            )

            write_klines_csv(
                validation_candles,
                validation_path
            )

            log(
                "SYSTEM",
                (
                    "OPTIMIZER REAL DATA READY "
                    f"symbol={symbol} "
                    f"train_candles={len(train_candles)} "
                    f"validation_candles={len(validation_candles)}"
                ),
                "SUCCESS"
            )

            train_paths.append(
                train_path
            )

            validation_paths.append(
                validation_path
            )

        self.TRAIN_DATASETS = train_paths

        # NOTE: ReplayEngine/MetricsEngine process one CSV at a time
        # under a single user_id -- the existing single-file
        # VALIDATION_DATASET contract is kept by validating against
        # each symbol's file in turn rather than changing the
        # downstream walk-forward step's shape. See optimize()'s
        # walk-forward section, which now iterates
        # self.VALIDATION_DATASETS.
        self.VALIDATION_DATASETS = validation_paths

        self.VALIDATION_DATASET = validation_paths[0]

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

        # =================================================
        # MINIMUM RISK/REWARD PRE-FILTER
        # =================================================
        #
        # tp_multiplier / sl_multiplier is the resulting
        # risk/reward ratio for every trade this combination
        # would produce -- RiskAgent rejects any signal below
        # settings.MINIMUM_RISK_REWARD_RATIO (LOW_RR) regardless
        # of structure/ATR/anything else. Previously every
        # combination ran a full replay (thousands of candles)
        # before this was discovered indirectly, when it scored
        # zero approved trades and got dropped by the
        # total_trades < 5 check below -- wasting the bulk of the
        # optimizer's runtime on combinations that were
        # mathematically guaranteed to fail. Skipping them here
        # means every combination that does reach replay has at
        # least a chance of producing real trades.

        minimum_rr = (
            settings.MINIMUM_RISK_REWARD_RATIO
        )

        combinations = []

        skipped = 0

        for tp, sl, trailing in product(
            atr_take_profit_values,
            atr_stop_values,
            atr_trailing_values
        ):

            risk_reward = (
                tp / sl
            )

            if risk_reward < minimum_rr:

                skipped += 1

                continue

            combinations.append({

                "atr_take_profit_multiplier": tp,

                "atr_stop_multiplier": sl,

                "atr_trailing_multiplier": trailing
            })

        if skipped:

            log(
                "OPTIMIZER",
                (
                    "PRE-FILTERED "
                    f"{skipped} combinations below "
                    f"MINIMUM_RISK_REWARD_RATIO={minimum_rr} "
                    "-- LOW_RR would have rejected every "
                    "signal these would have produced"
                ),
                "WARNING"
            )

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

            write_progress(
                current=index,
                total=len(combinations),
                phase=(
                    f"Testando combinação {index} de {len(combinations)}: "
                    f"TP×{params.get('atr_take_profit_multiplier')} "
                    f"SL×{params.get('atr_stop_multiplier')}"
                )
            )

            apply_config(
                params
            )

            trades_repository.reset(
                user_id=self.USER_ID
            )

            for dataset in self.TRAIN_DATASETS:

                log(
                    "DATASET",
                    dataset
                )

                market_structure_service.reset()

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

            # =================================================
            # FILTER INVALID CONFIGS
            # =================================================

            if metrics["profit_factor"] <= 1.0:
                continue

            if metrics["pnl"] <= 0:
                continue

            if metrics["expectancy"] <= 0:
                continue

            results.append({

                "params": dict(params),

                "metrics": dict(metrics),

                "score": score
            })

            restore_config(
                snapshot
            )

        # =====================================================
        # NO VALID RESULTS
        # =====================================================

        if not results:

            ReportRenderer.print_header(
                "OPTIMIZER VALIDATION REPORT"
            )

            ReportRenderer.print_section(
                "RESULT"
            )

            ReportRenderer.print_metric(
                "Configurations Tested",
                len(combinations)
            )

            ReportRenderer.print_metric(
                "Valid Configurations",
                0
            )

            ReportRenderer.print_metric(
                "Status",
                "NO_EDGE_FOUND"
            )

            print()

            print(
                "No configuration passed the "
                "minimum quantitative filters."
            )

            print()

            print(
                "Possible causes:"
            )

            print(
                "- Strategy lacks statistical edge"
            )

            print(
                "- Dataset too adverse"
            )

            print(
                "- Risk parameters too restrictive"
            )

            print(
                "- Insufficient trade sample"
            )

            print()

            print("=" * 60)

            restore_config(
                snapshot
            )

            return

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
        # WALK FORWARD VALIDATION
        # =====================================================

        write_progress(
            current=len(combinations),
            total=len(combinations),
            phase="Validação walk-forward…"
        )

        print()

        print("=" * 60)
        print("              WALK FORWARD VALIDATION")
        print("=" * 60)

        apply_config(
            best_result["params"]
        )

        trades_repository.reset(
            user_id=self.USER_ID
        )

        market_structure_service.reset()

        validation_datasets = getattr(
            self,
            "VALIDATION_DATASETS",
            [self.VALIDATION_DATASET]
        )

        for dataset in validation_datasets:

            log(
                "DATASET",
                dataset
            )

            validation_replay = (
                ReplayEngine(
                    csv_path=dataset,
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

        verdict = report["final_verdict"]

        config_save_allowed = (
            verdict["status"]
            not in self.BLOCKING_VERDICTS
        )

        # =====================================================
        # OPTIMIZER VALIDATION REPORT
        # =====================================================

        performance = report["performance"]

        trade_quality = report["trade_quality"]

        risk = report["risk"]

        stats = report["statistical_analysis"]

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
        # BEST TRAINING CONFIG
        # =====================================================

        ReportRenderer.print_header(
            "BEST TRAINING CONFIG"
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
            "Best Training Score",
            best_result["score"]
        )

        ReportRenderer.print_metric(
            "Best Training PF",
            best_result["metrics"]["profit_factor"]
        )

        ReportRenderer.print_metric(
            "Best Training Winrate",
            f"{best_result['metrics']['winrate']:.2%}"
        )

        # =====================================================
        # CONFIG EXPORT
        # =====================================================

        ReportRenderer.print_header(
            "CONFIG EXPORT"
        )

        if config_save_allowed:

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
                    best_result["params"],
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

            ReportRenderer.print_metric(
                "Generated File",
                "core/config/best_config.json"
            )

            ReportRenderer.print_metric(
                "Export Status",
                "SUCCESS"
            )

        else:

            log(
                "SYSTEM",
                (
                    "BEST CONFIG SAVE BLOCKED "
                    f"verdict={verdict['status']} -- "
                    "walk-forward validation flagged this result "
                    "as unreliable; the previous best_config.json "
                    "(if any) was left untouched"
                ),
                "WARNING"
            )

            ReportRenderer.print_metric(
                "Generated File",
                "NONE (save blocked)"
            )

            ReportRenderer.print_metric(
                "Export Status",
                f"BLOCKED ({verdict['status']})"
            )

        ReportRenderer.print_footer()

        restore_config(
            snapshot
        )

        clear_progress()


if __name__ == "__main__":

    import argparse

    from core.utils.event_loop import configure_event_loop
    from data.storage.database import init_db

    configure_event_loop()
    init_db()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--days",
        type=int,
        default=None,
        choices=[30, 60, 90],
        help="Dias de histórico a baixar (30, 60 ou 90)"
    )

    args = parser.parse_args()

    OptimizerEngine(
        history_days=args.days
    ).optimize()
