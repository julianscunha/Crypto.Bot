# -*- coding: utf-8 -*-

"""
Unit tests for apps/main.py

apps/main.py is primarily a multiprocessing launcher script (spawns
the API and trader as separate OS processes, blocks in an infinite
loop, handles Ctrl+C). That orchestration lives entirely under
`if __name__ == "__main__":` and isn't meaningfully unit-testable
without actually spawning processes. terminate_process() is the one
piece of standalone, directly testable logic.
"""

from unittest.mock import MagicMock

from apps.main import terminate_process


class TestTerminateProcess:

    def test_does_nothing_if_process_not_alive(self):

        proc = MagicMock()

        proc.is_alive.return_value = False

        terminate_process(proc, "TEST")

        proc.terminate.assert_not_called()

    def test_terminates_alive_process_gracefully(self):

        proc = MagicMock()

        # alive initially, then reports not alive after join (clean exit)
        proc.is_alive.side_effect = [True, False]

        terminate_process(proc, "TEST")

        proc.terminate.assert_called_once()

        proc.join.assert_called_once_with(timeout=5)

        proc.kill.assert_not_called()

    def test_force_kills_process_that_does_not_terminate(self):

        proc = MagicMock()

        # alive initially, still alive after join -> force kill path
        proc.is_alive.side_effect = [True, True]

        terminate_process(proc, "TEST")

        proc.terminate.assert_called_once()

        proc.kill.assert_called_once()
