# -*- coding: utf-8 -*-

"""
Regression tests for core/utils/console_logger.py's
WindowsSafeRotatingFileHandler.

Bug fixed: RotatingFileHandler.doRollover() calls os.rename() on the
log file. On Windows specifically, renaming a file that's still open
in another handle -- e.g. running the Optimizer while the Runner is
still active, or two processes both logging to the same
logs/runtime.log -- raises PermissionError ([WinError 32]). The
stdlib's default behavior lets that exception propagate out of every
log call until rotation succeeds, which crashed
OptimizerEngine.optimize() entirely (confirmed via a real user
traceback). Linux/macOS don't have this restriction, which is why it
was never caught in this project's Linux-based test/dev environment.
"""

import logging

import os

from unittest.mock import patch

from core.utils.console_logger import (
    WindowsSafeRotatingFileHandler
)


def _make_handler(tmp_path, max_bytes=10, backup_count=3):

    log_path = str(
        tmp_path / "test.log"
    )

    return WindowsSafeRotatingFileHandler(

        log_path,

        maxBytes=max_bytes,

        backupCount=backup_count,

        encoding="utf-8"
    ), log_path


def _make_record(message="a message long enough to trigger rollover"):

    return logging.LogRecord(
        "test",
        logging.INFO,
        "",
        0,
        message,
        (),
        None
    )


class TestWindowsSafeRotatingFileHandler:

    def test_normal_rotation_still_works(self, tmp_path):

        handler, log_path = _make_handler(tmp_path)

        record = _make_record()

        handler.emit(record)

        handler.emit(record)

        handler.emit(record)

        handler.close()

        rotated_files = sorted(
            os.listdir(tmp_path)
        )

        assert "test.log" in rotated_files

        assert "test.log.1" in rotated_files

    def test_survives_permission_error_during_rollover(
        self,
        tmp_path
    ):

        handler, log_path = _make_handler(tmp_path)

        record = _make_record()

        with patch(
            "os.rename",
            side_effect=PermissionError(
                "[WinError 32] simulated file lock "
                "by another process"
            )
        ):

            # must not raise -- this is exactly what crashed
            # OptimizerEngine.optimize() before the fix
            handler.emit(record)

        handler.close()

        assert os.path.exists(
            log_path
        )

    def test_log_content_is_preserved_through_a_failed_rollover(
        self,
        tmp_path
    ):

        handler, log_path = _make_handler(tmp_path)

        record = _make_record(
            "this message must survive"
        )

        with patch(
            "os.rename",
            side_effect=PermissionError(
                "[WinError 32] simulated file lock"
            )
        ):

            handler.emit(record)

        handler.close()

        with open(log_path) as f:

            content = f.read()

        assert "this message must survive" in content

    def test_handler_remains_usable_after_a_failed_rollover(
        self,
        tmp_path
    ):

        handler, log_path = _make_handler(tmp_path)

        record = _make_record()

        with patch(
            "os.rename",
            side_effect=PermissionError(
                "[WinError 32] simulated file lock"
            )
        ):

            handler.emit(record)

        # the next emit (rollover lock now simulated as released)
        # must not raise either -- the handler's stream must not be
        # left closed/broken by the failed rollover attempt
        second_record = _make_record(
            "a second message after the lock clears"
        )

        handler.emit(second_record)

        handler.close()

        with open(log_path) as f:

            content = f.read()

        assert "a second message after the lock clears" in content

    def test_only_permission_error_is_caught(self, tmp_path):

        # a genuinely different failure during rollover (disk full,
        # corrupted handle, etc.) should NOT be silently swallowed --
        # only the specific Windows file-lock scenario this fix
        # targets. Testing doRollover() directly here rather than
        # through emit(), since logging.Handler.emit() always
        # swallows exceptions via handleError() regardless of what
        # the handler itself does -- that's a property of the
        # logging module, not something this fix changes or should
        # be tested through.
        handler, log_path = _make_handler(tmp_path)

        with patch(
            "os.rename",
            side_effect=OSError(
                "some other unrelated OS error"
            )
        ):

            try:

                handler.doRollover()

                raised = False

            except OSError:

                raised = True

        handler.close()

        assert raised is True


class TestTaggedFilename:

    """
    Regression coverage for the PER-PROCESS LOG FILE fix: API,
    Runner, and Optimizer/Backtest subprocesses used to all share the
    same runtime.log/errors.log. Multiple OS processes independently
    opening and writing to the same file is not synchronized by
    stdlib logging at all -- confirmed directly that concurrent
    writes from two processes silently corrupt/drop each other's log
    lines, no exception raised anywhere. _tagged_filename() is what
    gives each process (Runner, Optimizer, Backtest -- see
    apps/trader/runner.py and apps/api/main.py's
    _run_job_subprocess_inner) its own file instead.
    """

    def test_no_tag_leaves_filename_unchanged(self):

        # Patch rather than rely on the module's ambient
        # _LOG_PROCESS_TAG: importing apps.trader.runner ANYWHERE
        # earlier in this test session (e.g. test_trader_runner.py)
        # sets the real CRYPTO_BOT_LOG_PROCESS env var process-wide,
        # and whichever module first imports console_logger afterward
        # freezes that tag into _LOG_PROCESS_TAG for the rest of the
        # process -- so the "no tag" case has to be forced here to
        # stay correct regardless of test/import order.
        import core.utils.console_logger as console_logger

        with patch.object(
            console_logger,
            "_LOG_PROCESS_TAG",
            ""
        ):

            assert (
                console_logger._tagged_filename("runtime.log")
                == "runtime.log"
            )

    def test_tag_from_env_is_applied(self):

        # _tagged_filename() itself doesn't read the env var directly
        # (that happens once, at import time, into _LOG_PROCESS_TAG)
        # -- this test locks in the string transform the module-level
        # RUNTIME_LOG_FILE/ERROR_LOG_FILE construction relies on.
        # Setting the env var itself is exercised end-to-end by
        # TestPerProcessLogFileAtImport below.
        import core.utils.console_logger as console_logger

        with patch.object(
            console_logger,
            "_LOG_PROCESS_TAG",
            "runner"
        ):

            assert (
                console_logger._tagged_filename("runtime.log")
                == "runtime-runner.log"
            )

            assert (
                console_logger._tagged_filename("errors.log")
                == "errors-runner.log"
            )


class TestPerProcessLogFileAtImport:

    def test_runner_process_gets_its_own_log_files(self):

        # Import in a fresh subprocess rather than reloading
        # core.utils.console_logger in-process: RUNTIME_LOG_FILE/
        # ERROR_LOG_FILE and the runtime_logger/error_logger handlers
        # are all computed once at module import time against the
        # REAL project root -- reloading here would silently break
        # tests/conftest.py's session-wide log-isolation fixture
        # (which patches those loggers' handlers by name, once, for
        # every other test in the suite) for the remainder of the
        # session.
        import subprocess
        import sys

        env = os.environ.copy()
        env["CRYPTO_BOT_LOG_PROCESS"] = "runner"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from core.utils.console_logger import "
                    "RUNTIME_LOG_FILE, ERROR_LOG_FILE; "
                    "print(RUNTIME_LOG_FILE.name); "
                    "print(ERROR_LOG_FILE.name)"
                )
            ],
            cwd=os.path.join(
                os.path.dirname(__file__),
                ".."
            ),
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        lines = result.stdout.strip().splitlines()

        assert lines == [
            "runtime-runner.log",
            "errors-runner.log"
        ]

    def test_untagged_process_keeps_default_filenames(self):

        import subprocess
        import sys

        env = os.environ.copy()
        env.pop("CRYPTO_BOT_LOG_PROCESS", None)

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from core.utils.console_logger import "
                    "RUNTIME_LOG_FILE, ERROR_LOG_FILE; "
                    "print(RUNTIME_LOG_FILE.name); "
                    "print(ERROR_LOG_FILE.name)"
                )
            ],
            cwd=os.path.join(
                os.path.dirname(__file__),
                ".."
            ),
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        lines = result.stdout.strip().splitlines()

        assert lines == [
            "runtime.log",
            "errors.log"
        ]
