# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)

# =====================================================
# LOG DIRECTORY
# =====================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

LOGS_DIR = ROOT_DIR / "logs"

LOGS_DIR.mkdir(
    exist_ok=True
)

RUNTIME_LOG_FILE = (
    LOGS_DIR / "runtime.log"
)

ERROR_LOG_FILE = (
    LOGS_DIR / "errors.log"
)

# =====================================================
# LOGGER
# =====================================================

def log(
    category: str,
    message: str,
    color=Fore.WHITE
) -> None:

    timestamp = (
        datetime.now()
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    category_label = (
        f"[{category}]"
        .ljust(24)
    )

    line = (
        f"{timestamp} "
        f"{category_label} "
        f"{message}"
    )

    # =================================================
    # CONSOLE
    # =================================================

    print(
        color
        + line
        + Style.RESET_ALL
    )

    # =================================================
    # FILE LOG
    # =================================================

    with open(
        RUNTIME_LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(line + "\n")

    # =================================================
    # ERROR LOG
    # =================================================

    if "ERROR" in category.upper():

        with open(
            ERROR_LOG_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(line + "\n")