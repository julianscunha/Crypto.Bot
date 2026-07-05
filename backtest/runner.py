# -*- coding: utf-8 -*-

import asyncio

from backtest.reports.progress_writer import (
    write_progress,
    clear_progress
)

from data.storage.database import (
    init_db
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from backtest.engine.replay_engine import (
    ReplayEngine
)

from backtest.engine.metrics_engine import (
    MetricsEngine
)

from backtest.engine.report_engine import (
    ReportEngine
)

from backtest.reports.validation_interpreter import (
    validation_interpreter
)

from backtest.reports.report_renderer import (
    ReportRenderer
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
    write_klines_csv,
    BinanceHistoryError
)


SYNTHETIC_DATASETS = [

    "backtest/datasets/bullish.csv",

    "backtest/datasets/bearish.csv",

    "backtest/datasets/sideways.csv",

    "backtest/datasets/volatile.csv"
]

USER_ID = 999

# =====================================================
# REAL HISTORICAL DATA
# =====================================================
#
# Same convention as backtest/optimizer/optimizer_engine.py's
# OptimizerEngine._prepare_datasets(): fetch real market history from
# Binance's public klines endpoint before backtesting, instead of
# always replaying the same small, fixed synthetic CSVs. Falls back
# to those synthetic datasets (with a clear warning, never a crash)
# if the fetch fails for any reason -- a network hiccup must never
# block running a backtest at all, it should just visibly use
# weaker data.
#
# Unlike the optimizer, this has no train/validation split: a
# regular backtest run is evaluating the CURRENT configured strategy
# against real history, not tuning/selecting parameters, so there's
# no overfitting risk from "validating" against the same data it ran
# against.

HISTORY_DAYS = 90

HISTORY_OUTPUT_DIR = "backtest/datasets/live_history"


async def prepare_datasets():

    try:

        return await _fetch_real_datasets()

    except Exception as error:

        log(
            "SYSTEM",
            (
                "BACKTEST REAL DATA FETCH FAILED "
                f"{error} -- falling back to synthetic "
                "example datasets in backtest/datasets/"
            ),
            "WARNING"
        )

        return SYNTHETIC_DATASETS


async def _fetch_real_datasets():

    symbols = settings.SYMBOLS

    interval = settings.KLINE_INTERVAL

    log(
        "SYSTEM",
        (
            "BACKTEST FETCHING REAL HISTORY "
            f"symbols={symbols} interval={interval} "
            f"days={HISTORY_DAYS}"
        )
    )

    dataset_paths = []

    for symbol in symbols:

        candles = await fetch_historical_klines(
            symbol=symbol,
            interval=interval,
            days=HISTORY_DAYS
        )

        if not candles:

            raise BinanceHistoryError(
                f"No historical candles returned for {symbol}"
            )

        dataset_path = (
            f"{HISTORY_OUTPUT_DIR}/{symbol.lower()}_backtest.csv"
        )

        write_klines_csv(
            candles,
            dataset_path
        )

        log(
            "SYSTEM",
            (
                "BACKTEST REAL DATA READY "
                f"symbol={symbol} candles={len(candles)}"
            ),
            "SUCCESS"
        )

        dataset_paths.append(
            dataset_path
        )

    return dataset_paths


async def main():

    print()

    print("=" * 60)
    print("                 BACKTEST ENGINE")
    print("=" * 60)

    print()

    # =====================================================
    # DATASETS (REAL HISTORY, WITH SYNTHETIC FALLBACK)
    # =====================================================

    datasets = await prepare_datasets()

    # =====================================================
    # STARTUP
    # =====================================================

    log(
        "SYSTEM",
        "MODE           BACKTEST"
    )

    log(
        "SYSTEM",
        f"DATASETS       {len(datasets)}"
    )

    log(
        "SYSTEM",
        "DATABASE       CONNECTED"
    )

    # =====================================================
    # DATABASE
    # =====================================================

    init_db()

    # =====================================================
    # RESET STATE
    # =====================================================

    trades_repository.reset(
        user_id=USER_ID
    )

    log(
        "SYSTEM",
        "TRADES         RESET"
    )

    # =====================================================
    # REPLAY ENGINE
    # =====================================================

    for idx, dataset in enumerate(datasets, start=1):

        print()

        print(
            "=" * 20
            + f" {dataset.split('/')[-1]} "
            + "=" * 20
        )

        write_progress(
            current=idx,
            total=len(datasets),
            phase=(
                f"Processando dataset {idx} de {len(datasets)}: "
                f"{dataset.split('/')[-1]}"
            )
        )

        market_structure_service.reset()

        replay = (
            ReplayEngine(
                csv_path=dataset,
                user_id=USER_ID
            )
        )

        await replay.replay()

    clear_progress()

    # =====================================================
    # METRICS
    # =====================================================

    metrics = (
        MetricsEngine()
        .generate(USER_ID)
    )

    # =====================================================
    # INTERPRETATION
    # =====================================================

    report = (
        validation_interpreter.analyze(
            metrics
        )
    )

    # =====================================================
    # BACKTEST VALIDATION REPORT
    # =====================================================

    performance = report["performance"]

    trade_quality = report["trade_quality"]

    risk = report["risk"]

    stats = report["statistical_analysis"]

    verdict = report["final_verdict"]

    ReportRenderer.print_header(
        "BACKTEST VALIDATION REPORT"
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

    ReportRenderer.print_footer()
    
    # =====================================================
    # REPORT
    # =====================================================

    ReportEngine().generate(
        metrics=metrics,
        output_path=(
            "backtest/reports/"
            "report.json"
        )
    )

    print()

    log(
        "SYSTEM",
        (
            "REPORT         "
            "backtest/reports/report.json"
        )
    )

    print()


if __name__ == "__main__":

    from core.utils.event_loop import configure_event_loop

    configure_event_loop()

    asyncio.run(main())