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
# LOG COLORS
# =====================================================

LOG_COLORS = {

    # ==============================================
    # NEUTRAL
    # ==============================================

    "MARKET": Fore.LIGHTWHITE_EX,
    "STRATEGY": Fore.LIGHTWHITE_EX,
    "RISK": Fore.LIGHTWHITE_EX,
    "POSITION": Fore.LIGHTWHITE_EX,
    "EXECUTION": Fore.LIGHTWHITE_EX,
    "SYSTEM": Fore.LIGHTWHITE_EX,

    "INFO": Fore.LIGHTWHITE_EX,

    "SUCCESS": Fore.GREEN,

    "ERROR": Fore.RED,

    "WARNING": Fore.YELLOW
}

# =====================================================
# LOGGER
# =====================================================

def log(
    category: str,
    message: str,
    level: str = "INFO"
) -> None:

    timestamp = (
        datetime.now()
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    category_label = (
        f"[{category}]"
        .ljust(16)
    )

    line = (
        f"{timestamp} "
        f"{category_label} "
        f"{message}"
    )

    # =================================================
    # CONSOLE
    # =================================================

    tag_color = LOG_COLORS.get(
        level,
        Fore.LIGHTWHITE_EX
    )

    console_line = (

        Fore.LIGHTWHITE_EX +

        f"{timestamp} " +

        tag_color +

        f"{category_label} " +

        Fore.LIGHTWHITE_EX +

        f"{message}" +

        Style.RESET_ALL
    )

    print(
        console_line
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

    if level == "ERROR":

        with open(
            ERROR_LOG_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(line + "\n")