# -*- coding: utf-8 -*-

import logging

from pathlib import Path

from datetime import (
    datetime
)

from logging.handlers import (
    RotatingFileHandler
)

from colorama import (

    Fore,

    Style,

    init
)

from core.config.logging_config import (
    LOGGING_CONFIG
)

# =====================================================
# WINDOWS-SAFE ROTATING HANDLER
# =====================================================
#
# RotatingFileHandler.doRollover() calls os.rename() on the log
# file. On Windows specifically, renaming a file that's still open
# in another handle (a second process writing to the same
# runtime.log/errors.log -- e.g. running the Optimizer while the
# Runner is still active, or two Optimizer instances at once) raises
# PermissionError ([WinError 32]). The stdlib's default behavior lets
# that exception propagate out of every single log call until the
# file is rotated, which crashes whatever was running (confirmed:
# OptimizerEngine.optimize() dying mid-run from this). Linux/macOS
# don't have this restriction (a rename can replace an open file),
# which is why this was never seen there.
#
# This subclass catches exactly that failure mode during rollover
# and falls back to simply continuing to write to the existing file
# -- the log temporarily exceeds max_log_file_size until the lock
# clears and a later rollover succeeds, which is a far better
# outcome than losing the actual program run over a log housekeeping
# operation.

class WindowsSafeRotatingFileHandler(
    RotatingFileHandler
):

    def doRollover(self):

        try:

            super().doRollover()

        except PermissionError:

            # another process/handle still has the log file open --
            # skip rotation this time and keep writing to it. The
            # stream may have been closed by the base implementation
            # before the rename failed, so make sure it's usable
            # again before returning.
            if (
                self.stream is None
                or self.stream.closed
            ):

                self.stream = self._open()

# =====================================================
# COLORAMA
# =====================================================

init(
    autoreset=True
)

# =====================================================
# PATHS
# =====================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parents[
        LOGGING_CONFIG[
            "root_directory_depth"
        ]
    ]
)

LOGS_DIR = (
    ROOT_DIR
    /
    LOGGING_CONFIG[
        "logs_directory"
    ]
)

LOGS_DIR.mkdir(
    exist_ok=True
)

RUNTIME_LOG_FILE = (
    LOGS_DIR
    /
    LOGGING_CONFIG[
        "runtime_log_filename"
    ]
)

ERROR_LOG_FILE = (
    LOGS_DIR
    /
    LOGGING_CONFIG[
        "error_log_filename"
    ]
)

# =====================================================
# VISUAL CONFIG
# =====================================================

CATEGORY_WIDTH = (
    LOGGING_CONFIG[
        "category_width"
    ]
)

SECTION_WIDTH = (
    LOGGING_CONFIG[
        "section_width"
    ]
)

TIMESTAMP_FORMAT = (
    LOGGING_CONFIG[
        "timestamp_format"
    ]
)

# =====================================================
# COLORS
# =====================================================

LOG_COLORS = {

    "INFO":
        Fore.LIGHTWHITE_EX,

    "SUCCESS":
        Fore.GREEN,

    "WARNING":
        Fore.LIGHTYELLOW_EX,

    "ERROR":
        Fore.RED,

    "DEBUG":
        Fore.LIGHTBLACK_EX
}

# =====================================================
# LOGGER FACTORY
# =====================================================

def build_logger(
    name: str,
    level: int,
    filename: Path
):

    logger = logging.getLogger(
        name
    )

    logger.setLevel(
        level
    )

    # =================================================
    # PREVENT DUPLICATION
    # =================================================

    logger.handlers.clear()

    handler = WindowsSafeRotatingFileHandler(

        filename,

        maxBytes=LOGGING_CONFIG[
            "max_log_file_size"
        ],

        backupCount=LOGGING_CONFIG[
            "log_backup_count"
        ],

        encoding="utf-8"
    )

    formatter = logging.Formatter(

        LOGGING_CONFIG[
            "file_log_format"
        ]
    )

    handler.setFormatter(
        formatter
    )

    logger.addHandler(
        handler
    )

    logger.propagate = False

    return logger

# =====================================================
# LOGGERS
# =====================================================

runtime_logger = build_logger(

    name="runtime_logger",

    level=logging.INFO,

    filename=RUNTIME_LOG_FILE
)

error_logger = build_logger(

    name="error_logger",

    level=logging.ERROR,

    filename=ERROR_LOG_FILE
)

# =====================================================
# HELPERS
# =====================================================

def build_log_line(
    timestamp: str,
    category: str,
    message: str
):

    category_label = (
        f"[{category}]"
        .ljust(CATEGORY_WIDTH)
    )

    return (

        f"{timestamp} "

        f"{category_label} "

        f"{message}"
    )


def build_console_line(
    timestamp: str,
    category: str,
    message: str,
    level: str
):

    category_label = (
        f"[{category}]"
        .ljust(CATEGORY_WIDTH)
    )

    level_color = (
        LOG_COLORS.get(

            level,

            Fore.LIGHTWHITE_EX
        )
    )

    return (

        Fore.LIGHTWHITE_EX

        + f"{timestamp} "

        + level_color

        + f"{category_label}"

        + Fore.LIGHTWHITE_EX

        + f" {message}"

        + Style.RESET_ALL
    )

# =====================================================
# LOGGER
# =====================================================

def log(
    category: str,
    message: str,
    level: str = "INFO"
) -> None:

    level = (
        str(level)
        .upper()
        .strip()
    )

    timestamp = (
        datetime.now()
        .strftime(
            TIMESTAMP_FORMAT
        )
    )

    log_line = build_log_line(

        timestamp=timestamp,

        category=category,

        message=message
    )

    console_line = build_console_line(

        timestamp=timestamp,

        category=category,

        message=message,

        level=level
    )

    # =================================================
    # CONSOLE
    # =================================================

    print(
        console_line
    )

    # =================================================
    # FILE LOGGING
    # =================================================

    runtime_logger.info(
        log_line
    )

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
