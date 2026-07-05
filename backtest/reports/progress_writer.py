# -*- coding: utf-8 -*-

"""
Escreve backtest/reports/progress.json durante a execução de jobs
(optimizer e backtest), para que a API possa fazer polling e o
frontend exibir uma barra de progresso real.

Uso:
    from backtest.reports.progress_writer import write_progress, clear_progress

    write_progress(current=3, total=24, phase="Testando combinações")
    clear_progress()
"""

import json

from pathlib import Path


PROGRESS_FILE = (
    Path(__file__)
    .resolve()
    .parent
    / "progress.json"
)


def write_progress(
    current: int,
    total: int,
    phase: str = ""
):

    percent = (
        round((current / total) * 100)
        if total > 0
        else 0
    )

    try:

        with open(
            PROGRESS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                {
                    "current": current,
                    "total": total,
                    "percent": percent,
                    "phase": phase
                },
                f
            )

    except OSError:

        pass


def clear_progress():

    try:

        PROGRESS_FILE.unlink(
            missing_ok=True
        )

    except OSError:

        pass
