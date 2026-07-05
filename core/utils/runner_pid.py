# -*- coding: utf-8 -*-

"""
Tracks the running apps/trader/runner.py process's PID on disk, so a
different process (the API, in core/services/process_manager_service.py)
can find and restart it.

Why this needs to exist at all: in Full Stack mode, the API and the
Runner are sibling processes both started by scripts/bootstrap/launcher.py
(see start_fullstack()) -- they share no in-memory state and the API
has no handle on the Runner's subprocess object. A PID file is the
simplest thing that survives across that process boundary.
"""

import os

from pathlib import Path


RUNNER_PID_FILE = (
    Path(__file__)
    .resolve()
    .parents[2]
    /
    "runtime"
    /
    "runner.pid"
)


def write_runner_pid():

    RUNNER_PID_FILE.parent.mkdir(
        parents=True,

        exist_ok=True
    )

    RUNNER_PID_FILE.write_text(
        str(
            os.getpid()
        )
    )


def clear_runner_pid():

    try:

        RUNNER_PID_FILE.unlink()

    except FileNotFoundError:

        pass


def read_runner_pid():

    """
    Returns the PID as an int, or None if no PID file exists or its
    content isn't a valid integer (e.g. corrupted/empty file --
    treated as "no known Runner process" rather than raising, since
    the caller's job is to restart the Runner either way).
    """

    try:

        content = (
            RUNNER_PID_FILE
            .read_text()
            .strip()
        )

        return int(
            content
        )

    except (
        FileNotFoundError,
        ValueError
    ):

        return None
