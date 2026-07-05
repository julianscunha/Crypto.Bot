# -*- coding: utf-8 -*-

"""
Unit tests for core/services/process_manager_service.py

== The zombie-process bug these tests guard against ==

Confirmed empirically while building this module: when THIS process
starts the Runner via subprocess.Popen and then sends it SIGTERM,
the child becomes a zombie until something calls Popen.wait()/
poll() on it. os.kill(pid, 0) and `ps -p <pid>` BOTH continue
reporting the zombie as "alive" indefinitely -- nothing else is
positioned to reap a child of this process. Popen.poll() returned
-15 (confirmed terminated) at the exact same real-world moment
`ps -p` still listed the process as running.

The fix keeps an in-memory handle (_managed_process) to processes
this module itself started, and prefers Popen.wait()/poll() for
liveness/termination whenever that handle exists -- falling back to
os.kill(pid, 0)/tasklist only when it doesn't (e.g. a Runner started
by a different process entirely).

These tests use a real, short-lived subprocess (a tiny Python
script that sleeps) rather than mocking subprocess.Popen, since the
bug being guarded against is specifically about real OS-level
process/zombie semantics that a mock would paper over.
"""

import subprocess

import sys

import time

import pytest

from core.services.process_manager_service import (
    start_runner,
    stop_runner,
    restart_runner,
    _is_process_alive,
    _terminate_pid,
    ProcessManagerError
)

import core.services.process_manager_service as pms_module

import core.utils.runner_pid as runner_pid_module


SLEEP_SCRIPT = (
    "import time, signal, sys; "
    "signal.signal(signal.SIGTERM, signal.SIG_DFL); "
    "time.sleep(30)"
)


@pytest.fixture(autouse=True)
def _isolate_pid_file(tmp_path, monkeypatch):

    """
    Redirects the PID file to an isolated tmp_path location for
    every test, and resets the module-level _managed_process handle
    before and after each test so tests never see state left behind
    by a previous one.
    """

    fake_pid_file = (
        tmp_path / "runner.pid"
    )

    monkeypatch.setattr(
        runner_pid_module,
        "RUNNER_PID_FILE",
        fake_pid_file
    )

    pms_module._managed_process = None

    yield

    if pms_module._managed_process is not None:

        try:

            pms_module._managed_process.kill()

            pms_module._managed_process.wait(
                timeout=3
            )

        except Exception:

            pass

    pms_module._managed_process = None

    try:

        fake_pid_file.unlink()

    except FileNotFoundError:

        pass


def _start_fake_runner_process():

    """
    Starts a real, short-lived subprocess standing in for the
    Runner -- a plain `python -c "time.sleep(30)"` rather than the
    actual apps.trader.runner module, since these tests are about
    process/signal/zombie mechanics, not the trading logic itself.
    Registers it as pms_module._managed_process, exactly like
    start_runner() does for a real Runner.
    """

    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            SLEEP_SCRIPT
        ]
    )

    pms_module._managed_process = process

    runner_pid_module.RUNNER_PID_FILE.write_text(
        str(process.pid)
    )

    return process


class TestZombieProcessHandling:

    def test_managed_process_is_detected_as_alive(self):

        process = _start_fake_runner_process()

        try:

            assert _is_process_alive(
                process.pid
            ) is True

        finally:

            process.kill()

            process.wait(
                timeout=3
            )

    def test_managed_process_termination_is_detected_quickly(
        self
    ):

        # this is the exact regression: terminating a process this
        # module started must be detected as dead within a couple
        # of seconds, not linger as an undetected zombie
        process = _start_fake_runner_process()

        _terminate_pid(
            process.pid
        )

        deadline = (
            time.monotonic()
            +
            5
        )

        detected_dead = False

        while time.monotonic() < deadline:

            if not _is_process_alive(
                process.pid
            ):

                detected_dead = True

                break

            time.sleep(0.1)

        assert detected_dead is True

    def test_stop_runner_completes_quickly_for_a_managed_process(
        self
    ):

        process = _start_fake_runner_process()

        start_time = time.monotonic()

        stop_runner()

        elapsed = (
            time.monotonic()
            -
            start_time
        )

        # before the fix, this same scenario took 10-15+ seconds
        # (the full graceful + force-kill timeout chain) because
        # the zombie was never detected as dead; after the fix it
        # completes within about a second
        assert elapsed < 5

        assert not _is_process_alive(
            process.pid
        )


class TestStopRunner:

    def test_no_pid_file_does_not_raise(self):

        stop_runner()

    def test_stale_pid_pointing_at_dead_process_does_not_raise(
        self
    ):

        runner_pid_module.RUNNER_PID_FILE.write_text(
            "999999999"
        )

        stop_runner()

        assert runner_pid_module.read_runner_pid() is None

    def test_clears_pid_file_after_successful_stop(self):

        _start_fake_runner_process()

        stop_runner()

        assert runner_pid_module.read_runner_pid() is None


class TestStartRunner:

    def test_writes_a_real_pid_file(self):

        # a real subprocess running apps.trader.runner imports
        # core.utils.runner_pid independently in its own process --
        # monkeypatching RUNNER_PID_FILE in THIS test process cannot
        # redirect where that child process writes its PID, so this
        # checks the real, actual project path rather than the
        # isolated tmp_path one used by the rest of this file
        import core.utils.runner_pid as real_runner_pid_module

        import importlib

        importlib.reload(
            real_runner_pid_module
        )

        process = start_runner()

        try:

            time.sleep(1)

            pid = real_runner_pid_module.read_runner_pid()

            assert pid == process.pid

        finally:

            process.kill()

            process.wait(
                timeout=5
            )

            real_runner_pid_module.clear_runner_pid()


class TestRestartRunner:

    def test_old_process_is_dead_and_new_one_is_different(self):

        old_process = _start_fake_runner_process()

        old_pid = old_process.pid

        new_process = restart_runner()

        try:

            assert new_process.pid != old_pid

            assert not _is_process_alive(
                old_pid
            )

            assert _is_process_alive(
                new_process.pid
            )

        finally:

            new_process.kill()

            new_process.wait(
                timeout=5
            )

    def test_raises_if_old_process_cannot_be_stopped(
        self,
        monkeypatch
    ):

        # force stop_runner's underlying termination to be a no-op,
        # simulating a process that refuses to die even after a
        # forced kill -- restart_runner must surface this loudly
        # rather than silently starting a second Runner alongside
        # one that might still be running
        _start_fake_runner_process()

        monkeypatch.setattr(
            pms_module,
            "_force_kill_pid",
            lambda pid: None
        )

        monkeypatch.setattr(
            pms_module,
            "TERMINATE_TIMEOUT_SECONDS",
            0.1
        )

        monkeypatch.setattr(
            pms_module,
            "FORCE_KILL_TIMEOUT_SECONDS",
            0.1
        )

        monkeypatch.setattr(
            pms_module,
            "_terminate_pid",
            lambda pid: None
        )

        with pytest.raises(ProcessManagerError):

            restart_runner()
