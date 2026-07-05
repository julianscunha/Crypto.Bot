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
