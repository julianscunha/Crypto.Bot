# -*- coding: utf-8 -*-

import asyncio

from colorama import (
    Fore,
    Style,
    init
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


DATASET = (
    "backtest/datasets/"
    "btcusdt_1m.csv"
)

USER_ID = 999


async def main():

    print()

    print(
        Fore.MAGENTA +
        "[BACKTEST]" +
        Style.RESET_ALL +
        " STARTING"
    )

    replay = (
        ReplayEngine(
            csv_path=DATASET,
            user_id=USER_ID
        )
    )

    await replay.replay()

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

    ReportEngine().generate(
        metrics=metrics,
        output_path=(
            "backtest/reports/"
            "report.json"
        )
    )


if __name__ == "__main__":

    asyncio.run(main())