# -*- coding: utf-8 -*-

import logging

from pathlib import Path
from datetime import datetime

from logging.handlers import (
    RotatingFileHandler
)

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)

# =====================================================
# LOG DIRECTORY
# =====================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

LOGS_DIR = (
    ROOT_DIR / "logs"
)

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
# VISUAL SETTINGS
# =====================================================

CATEGORY_WIDTH = 16

SECTION_WIDTH = 60

# =====================================================
# LOG COLORS
# =====================================================

LOG_COLORS = {

    # ==============================================
    # DEFAULT
    # ==============================================

    "INFO": Fore.LIGHTWHITE_EX,

    # ==============================================
    # SUCCESS
    # ==============================================

    "SUCCESS": Fore.GREEN,

    # ==============================================
    # WARNING
    # ==============================================

    "WARNING": Fore.LIGHTYELLOW_EX,

    # ==============================================
    # ERROR
    # ==============================================

    "ERROR": Fore.RED
}

# =====================================================
# PYTHON LOGGER
# =====================================================

runtime_logger = logging.getLogger(
    "runtime_logger"
)

runtime_logger.setLevel(
    logging.INFO
)

error_logger = logging.getLogger(
    "error_logger"
)

error_logger.setLevel(
    logging.ERROR
)

# =====================================================
# PREVENT DUPLICATE HANDLERS
# =====================================================

runtime_logger.handlers.clear()

error_logger.handlers.clear()

# =====================================================
# FILE HANDLERS
# =====================================================

runtime_handler = RotatingFileHandler(
    RUNTIME_LOG_FILE,
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8"
)

error_handler = RotatingFileHandler(
    ERROR_LOG_FILE,
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8"
)

runtime_logger.addHandler(
    runtime_handler
)

error_logger.addHandler(
    error_handler
)

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
        .ljust(CATEGORY_WIDTH)
    )

    log_line = (
        f"{timestamp} "
        f"{category_label} "
        f"{message}"
    )

    # =================================================
    # CONSOLE COLORS
    # =================================================

    level_color = LOG_COLORS.get(
        level,
        Fore.LIGHTWHITE_EX
    )

    console_line = (
        Fore.LIGHTWHITE_EX
        + f"{timestamp} "
        + level_color
        + f"{category_label}"
        + Fore.LIGHTWHITE_EX
        + f" {message}"
        + Style.RESET_ALL
    )

    print(
        console_line
    )

    # =================================================
    # RUNTIME LOG
    # =================================================

    runtime_logger.info(
        log_line
    )

    # =================================================
    # ERROR LOG
    # =================================================

    if level == "ERROR":

        error_logger.error(
            log_line
        )

# =====================================================
# SECTION
# =====================================================

def print_section(
    title: str
) -> None:

    cyan = (
        Fore.LIGHTCYAN_EX
    )

    line = (
        "=" * SECTION_WIDTH
    )

    print()

    print(
        cyan
        + line
        + Style.RESET_ALL
    )

    print(
        cyan
        + f"{title.center(SECTION_WIDTH)}"
        + Style.RESET_ALL
    )

    print(
        cyan
        + line
        + Style.RESET_ALL
    )

    print()