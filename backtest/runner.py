# -*- coding: utf-8 -*-

import asyncio

from colorama import (
    Fore,
    Style,
    init
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

init(autoreset=True)


DATASETS = [

    "backtest/datasets/bullish.csv",

    "backtest/datasets/bearish.csv",

    "backtest/datasets/sideways.csv",

    "backtest/datasets/volatile.csv"
]

USER_ID = 999


async def main():

    print()

    print(
        Fore.MAGENTA +
        "[BACKTEST]" +
        Style.RESET_ALL +
        " STARTING"
    )

    # =====================================================
    # DATABASE
    # =====================================================

    init_db()

    # =====================================================
    # RESET STATE
    # =====================================================

    trades_repository.reset()

    # =====================================================
    # REPLAY ENGINE
    # =====================================================

    for dataset in DATASETS:
    
        print()
    
        print(
            Fore.YELLOW +
            "[DATASET]" +
            Style.RESET_ALL +
            f" {dataset}"
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

    print()

    print(
        Fore.GREEN +
        "[BACKTEST]" +
        Style.RESET_ALL +
        f" Trades={metrics['total_trades']}"
    )

    print(
        Fore.GREEN +
        "[BACKTEST]" +
        Style.RESET_ALL +
        f" Winrate={metrics['winrate']}"
    )

    print(
        Fore.GREEN +
        "[BACKTEST]" +
        Style.RESET_ALL +
        f" PnL={metrics['pnl']}"
    )

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

    print(
        Fore.CYAN +
        "[BACKTEST REPORT]" +
        Style.RESET_ALL +
        " backtest/reports/report.json"
    )

    print()


if __name__ == "__main__":

    asyncio.run(main())