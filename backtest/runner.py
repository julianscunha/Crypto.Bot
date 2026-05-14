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
    # VALIDATION REPORT
    # =====================================================

    print()

    print("=" * 60)
    print("                 VALIDATION REPORT")
    print("=" * 60)

    print()

    # =====================================================
    # PERFORMANCE
    # =====================================================

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

    # =====================================================
    # TRADE QUALITY
    # =====================================================

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

    # =====================================================
    # RISK
    # =====================================================

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

    # =====================================================
    # STATISTICAL ANALYSIS
    # =====================================================

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

    # =====================================================
    # FINAL VERDICT
    # =====================================================

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