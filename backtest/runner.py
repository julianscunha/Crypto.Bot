# -*- coding: utf-8 -*-

import asyncio

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


DATASETS = [

    "backtest/datasets/bullish.csv",

    "backtest/datasets/bearish.csv",

    "backtest/datasets/sideways.csv",

    "backtest/datasets/volatile.csv"
]

USER_ID = 999


async def main():

    print()

    print("=" * 60)
    print("                 BACKTEST ENGINE")
    print("=" * 60)

    print()

    # =====================================================
    # STARTUP
    # =====================================================

    log(
        "SYSTEM",
        "MODE           BACKTEST"
    )

    log(
        "SYSTEM",
        f"DATASETS       {len(DATASETS)}"
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

    trades_repository.reset()

    log(
        "SYSTEM",
        "TRADES         RESET"
    )

    # =====================================================
    # REPLAY ENGINE
    # =====================================================

    for dataset in DATASETS:

        print()

        print(
            "=" * 20
            + f" {dataset.split('/')[-1]} "
            + "=" * 20
        )

        replay = (
            ReplayEngine(
                csv_path=dataset,
                user_id=USER_ID
            )
        )

        await replay.replay()

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

    asyncio.run(main())