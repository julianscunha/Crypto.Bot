# -*- coding: utf-8 -*-

import logging

import os

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

# =====================================================
# PER-PROCESS LOG FILE
# =====================================================
#
# API, Runner, and Optimizer/Backtest subprocesses all import this
# module and used to share the exact same runtime.log/errors.log
# files. WindowsSafeRotatingFileHandler above only guards against the
# rollover-time PermissionError crash -- it does nothing about the
# more basic problem that stdlib logging assumes a SINGLE process
# owns the file. Two OS processes each holding their own independent
# open handle and writing concurrently is not synchronized in any
# way: interleaved writes routinely smash two lines together into one
# unparseable line, silently destroying both (confirmed by
# reproducing it directly -- two processes logging 300 lines each
# concurrently lost dozens of lines apiece to corruption, no
# exception raised anywhere). That's why a live Runner session could
# show nothing recognizable in runtime.log despite the console
# clearly working the whole time: the API process (or an
# Optimizer/Backtest subprocess) was writing to the same file at the
# same time.
#
# Fix: give each process its own log file, named via an optional tag
# read from CRYPTO_BOT_LOG_PROCESS (set by the process itself before
# any other imports -- see apps/trader/runner.py -- or injected into
# a subprocess's environment by whatever spawned it -- see
# apps/api/main.py's _run_job_subprocess_inner). Unset/empty keeps
# the original runtime.log/errors.log filenames, so the API process
# (the "default" one most tooling/tests expect) needs no changes.

_LOG_PROCESS_TAG = (
    os.environ.get(
        "CRYPTO_BOT_LOG_PROCESS",
        ""
    )
    .strip()
    .lower()
)


def _tagged_filename(filename: str) -> str:

    if not _LOG_PROCESS_TAG:

        return filename

    stem, _, ext = filename.rpartition(".")

    return f"{stem}-{_LOG_PROCESS_TAG}.{ext}"


RUNTIME_LOG_FILE = (
    LOGS_DIR
    /
    _tagged_filename(
        LOGGING_CONFIG[
            "runtime_log_filename"
        ]
    )
)

ERROR_LOG_FILE = (
    LOGS_DIR
    /
    _tagged_filename(
        LOGGING_CONFIG[
            "error_log_filename"
        ]
    )
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

    "CRITICAL":
        Fore.MAGENTA,

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
# RUNTIME RETAG (for pool workers spawned after import)
# =====================================================
#
# CRYPTO_BOT_LOG_PROCESS only works for the *first* process to import
# this module -- everything above already ran by the time a
# ProcessPoolExecutor worker starts, because the worker has to import
# this module's owning package just to find the function it was told
# to run, and that import is what freezes _LOG_PROCESS_TAG from the
# inherited env var. So every worker in a pool would otherwise get the
# exact same tag as their parent (and each other) and silently share
# one log file again -- see backtest/optimizer/optimizer_engine.py's
# parallel combination workers, the first caller of this.

def retag_process(tag: str) -> None:

    global _LOG_PROCESS_TAG, RUNTIME_LOG_FILE, ERROR_LOG_FILE
    global runtime_logger, error_logger

    _LOG_PROCESS_TAG = tag.strip().lower()

    RUNTIME_LOG_FILE = (
        LOGS_DIR
        /
        _tagged_filename(
            LOGGING_CONFIG["runtime_log_filename"]
        )
    )

    ERROR_LOG_FILE = (
        LOGS_DIR
        /
        _tagged_filename(
            LOGGING_CONFIG["error_log_filename"]
        )
    )

    for handler in list(runtime_logger.handlers):
        handler.close()

    for handler in list(error_logger.handlers):
        handler.close()

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

    if level in (
        "ERROR",
        "CRITICAL"
    ):

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
