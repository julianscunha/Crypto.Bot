# -*- coding: utf-8 -*-

"""
Lets the API process restart the sibling Runner process.

In Full Stack mode (scripts/bootstrap/launcher.py's
start_fullstack()), the API and Runner are sibling subprocesses with
no shared in-memory state -- the API has no handle on the Runner's
subprocess object. core/utils/runner_pid.py's PID file is what
bridges that gap: the Runner writes its own PID on startup, and this
service reads it from the API process to find and terminate it, then
starts a fresh Runner process the same way
scripts/bootstrap/launcher.py's start_fullstack() does.

== Why a restart is needed for a mode change at all ==

core/config/settings.py's MODE/BINANCE_TESTNET/LIVE_TRADING_CONFIRMED
are read once, at Python import time. A running Runner process keeps
whatever values it started with regardless of what gets written to
.env afterward -- there's no in-process mechanism to make it pick up
a changed MODE. Restarting the process is what reloads settings.py
from the updated .env.

== The zombie-process bug this module works around ==

When THIS process starts the Runner via subprocess.Popen (as
start_runner() does), sending SIGTERM and then checking liveness via
os.kill(pid, 0) or `ps -p` is unreliable: once the child dies, it
becomes a zombie until its parent calls Popen.wait()/poll() on it,
and a zombie still shows up as "alive" to os.kill(pid, 0)/ps
indefinitely -- nothing else is positioned to reap a child of THIS
process. Confirmed this empirically while building it:
Popen.poll() returned -15 (confirmed terminated by SIGTERM) at the
exact same moment `ps -p <pid>` still listed the process as running.

The fix: keep an in-memory reference to the Popen object whenever
THIS process is the one that started the Runner, and prefer
Popen.wait()/poll() over os.kill(pid, 0)/ps for liveness and
termination whenever that handle exists. Only fall back to
os.kill(pid, 0)/tasklist when no such handle exists -- e.g. the
Runner was started by the original launcher terminal, not by this
API process, in which case the real parent (the launcher) is the one
positioned to reap it, and a zombie isn't a concern for an API
process that never had a handle on it to begin with.
"""

import os

import subprocess

import sys

import time

from pathlib import Path

from core.utils.runner_pid import (
    read_runner_pid,
    clear_runner_pid
)

from core.utils.console_logger import (
    log
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

TERMINATE_TIMEOUT_SECONDS = 10

FORCE_KILL_TIMEOUT_SECONDS = 5

STARTUP_GRACE_SECONDS = 1

# In-memory handle to the Popen object for a Runner THIS process
# started, if any -- see module docstring for why this is necessary
# rather than relying purely on the PID file + os.kill/ps.
_managed_process = None


class ProcessManagerError(
    Exception
):

    pass


def _is_process_alive(
    pid: int
) -> bool:

    if (
        _managed_process is not None
        and _managed_process.pid == pid
    ):

        # reaps the zombie if it has already exited, returning its
        # exit code -- None means still running
        return _managed_process.poll() is None

    try:

        if os.name == "nt":

            result = subprocess.run(
                [
                    "tasklist",

                    "/FI",

                    f"PID eq {pid}"
                ],

                capture_output=True,

                text=True
            )

            return str(pid) in result.stdout

        os.kill(
            pid,
            0
        )

        return True

    except (
        ProcessLookupError,
        PermissionError
    ):

        return False

    except OSError:

        return False


def _terminate_pid(
    pid: int
):

    if os.name == "nt":

        subprocess.run(
            [
                "taskkill",

                "/F",

                "/T",

                "/PID",

                str(pid)
            ],

            stdout=subprocess.DEVNULL,

            stderr=subprocess.DEVNULL
        )

        return

    if (
        _managed_process is not None
        and _managed_process.pid == pid
    ):

        _managed_process.terminate()

        return

    try:

        os.kill(
            pid,

            15  # SIGTERM
        )

    except ProcessLookupError:

        pass


def _force_kill_pid(
    pid: int
):

    """
    Escalation if _terminate_pid's graceful signal didn't work in
    time. On Windows, _terminate_pid's taskkill /F is already
    forceful -- there's no further escalation needed there, so this
    is a no-op on Windows and only does anything on Unix (SIGKILL).
    """

    if os.name == "nt":

        return

    if (
        _managed_process is not None
        and _managed_process.pid == pid
    ):

        _managed_process.kill()

        return

    try:

        os.kill(
            pid,

            9  # SIGKILL
        )

    except ProcessLookupError:

        pass


def _wait_until(
    pid: int,
    timeout_seconds: float
) -> bool:

    """
    Polls _is_process_alive(pid) until it reports dead or
    timeout_seconds elapses. Returns True if the process is
    confirmed dead within the timeout. When a managed Popen handle
    exists, this also reaps it via poll() on every iteration (see
    _is_process_alive), so the process never lingers as a zombie
    while this loop is the one watching it.
    """

    deadline = (
        time.monotonic()
        +
        timeout_seconds
    )

    while time.monotonic() < deadline:

        if not _is_process_alive(
            pid
        ):

            return True

        time.sleep(0.2)

    return not _is_process_alive(
        pid
    )


def stop_runner():

    """
    Terminates the currently-running Runner process, if one is
    known via the PID file. Waits up to TERMINATE_TIMEOUT_SECONDS
    for a graceful exit, then escalates to a forceful kill and waits
    up to FORCE_KILL_TIMEOUT_SECONDS more. A missing PID file or an
    already-dead PID is treated as "nothing to stop", not an error
    -- the caller (restart_runner) always proceeds to start a fresh
    process either way.
    """

    global _managed_process

    pid = read_runner_pid()

    if pid is None:

        log(
            "SYSTEM",
            "RUNNER STOP -- no known Runner process (PID file absent)",
            "WARNING"
        )

        return

    if not _is_process_alive(
        pid
    ):

        log(
            "SYSTEM",
            (
                "RUNNER STOP -- PID "
                f"{pid} from PID file is no longer running"
            ),
            "WARNING"
        )

        clear_runner_pid()

        _managed_process = None

        return

    log(
        "SYSTEM",
        f"RUNNER STOP -- terminating PID {pid}",
        "WARNING"
    )

    _terminate_pid(
        pid
    )

    if _wait_until(
        pid,
        TERMINATE_TIMEOUT_SECONDS
    ):

        clear_runner_pid()

        _managed_process = None

        return

    log(
        "SYSTEM",
        (
            "RUNNER STOP -- PID "
            f"{pid} did not exit gracefully within "
            f"{TERMINATE_TIMEOUT_SECONDS}s, forcing kill"
        ),
        "WARNING"
    )

    _force_kill_pid(
        pid
    )

    if not _wait_until(
        pid,
        FORCE_KILL_TIMEOUT_SECONDS
    ):

        log(
            "SYSTEM",
            (
                "RUNNER STOP -- PID "
                f"{pid} still running after forced kill"
            ),
            "ERROR"
        )

        raise ProcessManagerError(
            f"Runner process {pid} could not be terminated"
        )

    clear_runner_pid()

    _managed_process = None


def start_runner():

    """
    Starts a fresh Runner process the same way
    scripts/bootstrap/launcher.py's start_fullstack() does --
    `python -m apps.trader.runner` from the project root. The new
    process writes its own PID file on startup (see
    apps/trader/runner.py's entrypoint). The Popen handle is kept in
    _managed_process so this module can reliably detect when this
    specific process exits later (see module docstring).
    """

    global _managed_process

    process = subprocess.Popen(

        [
            sys.executable,

            "-m",

            "apps.trader.runner"
        ],

        cwd=str(
            PROJECT_ROOT
        )
    )

    _managed_process = process

    log(
        "SYSTEM",
        f"RUNNER START -- new process PID {process.pid}",
        "SUCCESS"
    )

    return process


def restart_runner():

    """
    Stops whatever Runner process is currently tracked (if any) and
    starts a fresh one, which will import core/config/settings.py
    fresh and pick up whatever MODE/BINANCE_TESTNET/
    LIVE_TRADING_CONFIRMED values are in .env at that moment.

    Raises ProcessManagerError if the old process couldn't be
    confirmed stopped -- never silently starts a second Runner
    alongside one that might still be running, since two Runner
    processes both managing the same account would be a much worse
    failure mode than simply reporting the restart failed.
    """

    stop_runner()

    time.sleep(
        STARTUP_GRACE_SECONDS
    )

    return start_runner()
