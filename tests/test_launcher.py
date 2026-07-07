# -*- coding: utf-8 -*-

"""
Regression tests for scripts/bootstrap/launcher.py

Bug #1 fixed: start_fullstack() unconditionally called
subprocess.Popen(["npm", "run", "dev"], cwd=ROOT/"frontend") before
starting anything else meaningful. At the time this was first
written, no frontend/ directory existed in the project, so this
crashed immediately with FileNotFoundError, without ever starting
the API or the trader -- the two backend components that do exist
and work. start_frontend() (menu option [4]) had the same
unconditional crash.

Bug #2 fixed: even after frontend/ was built and start_fullstack()
correctly guarded for its absence, subprocess.Popen(["npm", ...])
(without shell=True) raises FileNotFoundError ([WinError 2]) on
Windows specifically, because npm is actually npm.cmd there, and
CreateProcess doesn't resolve PATHEXT extensions the way a shell
does. This crashed Full Stack on Windows even with Node.js properly
installed. Fixed via shutil.which("npm"), which resolves to npm.cmd
on Windows and npm on Linux/macOS.

Bug #3 fixed: even after the npm.cmd resolution fix, a fresh
checkout's frontend/ has no node_modules/ (it's never shipped --
large and reproducible via `npm install`). Running `npm run dev`
(which is really just `vite`) before installing dependencies fails
with "'vite' is not recognized..." on Windows / "vite: not found" on
Linux. Fixed by detecting a missing node_modules/ and running
`npm install` automatically first, the same way install_requirements()
already does for the Python side.

Every test here mocks shutil.which() explicitly rather than relying
on npm actually being on PATH in the test environment, and patches
ROOT to an isolated tmp_path rather than relying on whether this
particular checkout happens to have a real frontend/ directory.
"""

import pytest

import subprocess

from unittest.mock import MagicMock, patch

from scripts.bootstrap.launcher import (
    frontend_available,
    frontend_dependencies_installed,
    install_frontend_dependencies,
    resolve_npm_command,
    terminate_process,
    start_frontend,
    start_fullstack
)


LINUX_NPM_PATH = "/usr/bin/npm"

WINDOWS_NPM_PATH = (
    "C:\\Program Files\\nodejs\\npm.cmd"
)


@pytest.fixture
def isolated_root_without_frontend(tmp_path):

    with patch(
        "scripts.bootstrap.launcher.ROOT",
        tmp_path
    ):

        yield tmp_path


@pytest.fixture
def isolated_root_with_frontend(tmp_path):

    (tmp_path / "frontend").mkdir()

    with patch(
        "scripts.bootstrap.launcher.ROOT",
        tmp_path
    ):

        yield tmp_path


class TestFrontendAvailable:

    def test_false_when_frontend_directory_does_not_exist(
        self,
        isolated_root_without_frontend
    ):

        assert frontend_available() is False

    def test_true_when_frontend_directory_exists(
        self,
        isolated_root_with_frontend
    ):

        assert frontend_available() is True


class TestTerminateProcess:

    def test_windows_uses_taskkill_tree_for_full_shutdown(
        self
    ):

        proc = MagicMock()
        proc.pid = 1234

        with patch("scripts.bootstrap.launcher.os.name", "nt"):
            with patch("scripts.bootstrap.launcher.subprocess.run") as mock_run:
                terminate_process(proc)

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        assert args[0] == [
            "taskkill",
            "/F",
            "/T",
            "/PID",
            "1234"
        ]
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        proc.wait.assert_called_once_with(timeout=5)
        proc.terminate.assert_not_called()


class TestResolveNpmCommand:

    def test_returns_none_when_npm_not_on_path(self):

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=None
        ):

            assert resolve_npm_command() is None

    def test_resolves_to_npm_cmd_on_windows(self):

        # this is the exact scenario that crashed with
        # FileNotFoundError ([WinError 2]) before the fix: npm.cmd
        # is the real executable on Windows, not "npm"
        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=WINDOWS_NPM_PATH
        ):

            command = resolve_npm_command()

            assert command == [
                WINDOWS_NPM_PATH,
                "run",
                "dev"
            ]

    def test_resolves_to_npm_on_linux(self):

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            command = resolve_npm_command()

            assert command == [
                LINUX_NPM_PATH,
                "run",
                "dev"
            ]


class TestStartFrontend:

    def test_does_not_raise_when_frontend_missing(
        self,
        isolated_root_without_frontend
    ):

        # previously: FileNotFoundError
        start_frontend()

    def test_does_not_attempt_popen_when_frontend_missing(
        self,
        isolated_root_without_frontend
    ):

        with patch(
            "scripts.bootstrap.launcher.subprocess.Popen"
        ) as mock_popen:

            start_frontend()

            mock_popen.assert_not_called()

    def test_starts_npm_dev_when_frontend_present(
        self,
        isolated_root_with_frontend
    ):

        fake_process = MagicMock()

        fake_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.frontend_dependencies_installed",
                return_value=True
            ):

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    return_value=fake_process
                ) as mock_popen:

                    start_frontend()

                    args, kwargs = mock_popen.call_args

                    assert args[0] == [
                        LINUX_NPM_PATH,
                        "run",
                        "dev"
                    ]

                    assert str(
                        isolated_root_with_frontend / "frontend"
                    ) == kwargs["cwd"]

    def test_does_not_raise_when_npm_not_on_path(
        self,
        isolated_root_with_frontend
    ):

        # regression: previously crashed with FileNotFoundError on
        # Windows when npm wasn't resolvable as a bare "npm" command
        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=None
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.Popen"
            ) as mock_popen:

                start_frontend()

                mock_popen.assert_not_called()


class TestStartFullstack:

    def test_does_not_raise_when_frontend_missing(
        self,
        isolated_root_without_frontend
    ):

        fake_api_process = MagicMock()

        fake_api_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.subprocess.Popen",
            side_effect=[fake_api_process]
        ) as mock_popen:

            start_fullstack()

            # Only API is started; Runner is no longer auto-started
            assert mock_popen.call_count == 1

    def test_does_not_raise_when_npm_not_on_path(
        self,
        isolated_root_with_frontend
    ):

        fake_api_process = MagicMock()

        fake_api_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=None
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.Popen",
                side_effect=[fake_api_process]
            ) as mock_popen:

                start_fullstack()

                # only API started; no runner, no frontend
                assert mock_popen.call_count == 1

    def test_starts_api_with_uvicorn_command(
        self,
        isolated_root_without_frontend
    ):

        fake_api_process = MagicMock()

        fake_runner_process = MagicMock()

        fake_runner_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.subprocess.Popen",
            side_effect=[
                fake_api_process,
                fake_runner_process
            ]
        ) as mock_popen:

            start_fullstack()

            first_call_args = mock_popen.call_args_list[0][0][0]

            assert "uvicorn" in first_call_args

            assert "apps.api.main:app" in first_call_args

    def test_api_log_level_suppresses_access_log_noise(
        self,
        isolated_root_without_frontend
    ):

        # regression: without --log-level warning, uvicorn's access
        # log prints an INFO line for every single request, including
        # every 3s/5s dashboard/health poll from the frontend -- this
        # drowns out the Runner's own signal/trade log lines in the
        # same terminal when running Full Stack. apps/main.py already
        # passes log_level="warning" via the Python API; this is the
        # equivalent for the subprocess.Popen-based uvicorn launch
        # here, which only logs warnings/errors, not every 200 OK.

        fake_api_process = MagicMock()

        fake_runner_process = MagicMock()

        fake_runner_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.subprocess.Popen",
            side_effect=[
                fake_api_process,
                fake_runner_process
            ]
        ) as mock_popen:

            start_fullstack()

            first_call_args = mock_popen.call_args_list[0][0][0]

            assert "--log-level" in first_call_args

            log_level_index = first_call_args.index(
                "--log-level"
            )

            assert (
                first_call_args[log_level_index + 1]
                == "warning"
            )

    def test_does_not_start_trader_runner_automatically(
        self,
        isolated_root_without_frontend
    ):

        # Bot now starts manually via the web interface (▶ button).
        # start_fullstack() should only launch the API process, not
        # the Runner -- users control the Runner lifecycle from the
        # frontend after the system is up.

        fake_api_process = MagicMock()

        fake_api_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.subprocess.Popen",
            side_effect=[fake_api_process]
        ) as mock_popen:

            start_fullstack()

            assert mock_popen.call_count == 1

            first_call_args = mock_popen.call_args_list[0][0][0]

            assert "uvicorn" in first_call_args

            # Runner must NOT have been started
            all_args = [
                call[0][0]
                for call in mock_popen.call_args_list
            ]

            assert not any(
                "apps.trader.runner" in str(args)
                for args in all_args
            )

    def test_terminates_api_process_on_completion(
        self,
        isolated_root_without_frontend
    ):

        fake_api_process = MagicMock()

        fake_api_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.subprocess.Popen",
            side_effect=[fake_api_process]
        ):

            with patch(
                "scripts.bootstrap.launcher.terminate_process"
            ) as mock_terminate:

                start_fullstack()

                terminated = [
                    call.args[0]
                    for call in mock_terminate.call_args_list
                ]

                assert fake_api_process in terminated

    def test_starts_frontend_too_when_available(
        self,
        isolated_root_with_frontend
    ):

        fake_api_process = MagicMock()

        fake_frontend_process = MagicMock()

        fake_frontend_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.frontend_dependencies_installed",
                return_value=True
            ):

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    side_effect=[
                        fake_api_process,
                        fake_frontend_process
                    ]
                ) as mock_popen:

                    start_fullstack()

                    # API + frontend only (runner no longer auto-started)
                    assert mock_popen.call_count == 2

                    second_call_args = mock_popen.call_args_list[1][0][0]

                    assert second_call_args == [
                        LINUX_NPM_PATH,
                        "run",
                        "dev"
                    ]

                    assert fake_frontend_process.wait.call_count >= 1

    def test_windows_npm_cmd_resolution_end_to_end(
        self,
        isolated_root_with_frontend
    ):

        fake_api_process = MagicMock()

        fake_frontend_process = MagicMock()

        fake_frontend_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=WINDOWS_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.frontend_dependencies_installed",
                return_value=True
            ):

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    side_effect=[
                        fake_api_process,
                        fake_frontend_process
                    ]
                ) as mock_popen:

                    start_fullstack()

                    second_call_args = mock_popen.call_args_list[1][0][0]

                    assert second_call_args[0] == WINDOWS_NPM_PATH


class TestFrontendDependenciesInstalled:

    def test_false_when_node_modules_missing(
        self,
        isolated_root_with_frontend
    ):

        assert frontend_dependencies_installed(
            [LINUX_NPM_PATH, "run", "dev"]
        ) is False

    def test_true_when_node_modules_present(
        self,
        isolated_root_with_frontend
    ):

        (
            isolated_root_with_frontend
            / "frontend"
            / "node_modules"
        ).mkdir()

        assert frontend_dependencies_installed(
            [LINUX_NPM_PATH, "run", "dev"]
        ) is True


class TestInstallFrontendDependencies:

    def test_runs_npm_install_in_frontend_directory(
        self,
        isolated_root_with_frontend
    ):

        fake_result = MagicMock(returncode=0)

        with patch(
            "scripts.bootstrap.launcher.subprocess.run",
            return_value=fake_result
        ) as mock_run:

            result = install_frontend_dependencies(
                LINUX_NPM_PATH
            )

            assert result is True

            args, kwargs = mock_run.call_args

            assert args[0] == [
                LINUX_NPM_PATH,
                "install"
            ]

            assert str(
                isolated_root_with_frontend / "frontend"
            ) == kwargs["cwd"]

    def test_returns_false_on_install_failure(
        self,
        isolated_root_with_frontend
    ):

        fake_result = MagicMock(returncode=1)

        with patch(
            "scripts.bootstrap.launcher.subprocess.run",
            return_value=fake_result
        ):

            result = install_frontend_dependencies(
                LINUX_NPM_PATH
            )

            assert result is False


class TestAutoInstallIntegration:

    def test_start_frontend_installs_deps_when_missing(
        self,
        isolated_root_with_frontend
    ):

        # regression: this exact scenario --frontend/ exists, npm
        # resolves, but node_modules/ is missing on a fresh
        # checkout-- previously failed with
        # "'vite' is not recognized..." (Windows) /
        # "vite: not found" (Linux) because npm run dev was invoked
        # before any dependencies were ever installed.

        fake_install_result = MagicMock(returncode=0)

        fake_dev_process = MagicMock()

        fake_dev_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.run",
                return_value=fake_install_result
            ) as mock_run:

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    return_value=fake_dev_process
                ) as mock_popen:

                    start_frontend()

                    # npm install ran first...
                    install_args = mock_run.call_args[0][0]

                    assert install_args == [
                        LINUX_NPM_PATH,
                        "install"
                    ]

                    # ...then npm run dev
                    dev_args = mock_popen.call_args[0][0]

                    assert dev_args == [
                        LINUX_NPM_PATH,
                        "run",
                        "dev"
                    ]

    def test_start_frontend_skips_install_when_already_present(
        self,
        isolated_root_with_frontend
    ):

        (
            isolated_root_with_frontend
            / "frontend"
            / "node_modules"
        ).mkdir()

        fake_dev_process = MagicMock()

        fake_dev_process.wait.return_value = None

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.run"
            ) as mock_run:

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    return_value=fake_dev_process
                ):

                    start_frontend()

                    mock_run.assert_not_called()

    def test_start_frontend_does_not_start_dev_server_when_install_fails(
        self,
        isolated_root_with_frontend
    ):

        fake_install_result = MagicMock(returncode=1)

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.run",
                return_value=fake_install_result
            ):

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen"
                ) as mock_popen:

                    start_frontend()

                    mock_popen.assert_not_called()

    def test_start_fullstack_installs_deps_when_missing(
        self,
        isolated_root_with_frontend
    ):

        fake_api_process = MagicMock()

        fake_frontend_process = MagicMock()

        fake_frontend_process.wait.return_value = None

        fake_install_result = MagicMock(returncode=0)

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.run",
                return_value=fake_install_result
            ) as mock_run:

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    side_effect=[
                        fake_api_process,
                        fake_frontend_process
                    ]
                ) as mock_popen:

                    start_fullstack()

                    assert mock_run.called

                    # API + frontend only (runner no longer auto-started)
                    assert mock_popen.call_count == 2

    def test_start_fullstack_falls_back_when_install_fails(
        self,
        isolated_root_with_frontend
    ):

        fake_api_process = MagicMock()

        fake_api_process.wait.return_value = None

        fake_install_result = MagicMock(returncode=1)

        with patch(
            "scripts.bootstrap.launcher.shutil.which",
            return_value=LINUX_NPM_PATH
        ):

            with patch(
                "scripts.bootstrap.launcher.subprocess.run",
                return_value=fake_install_result
            ):

                with patch(
                    "scripts.bootstrap.launcher.subprocess.Popen",
                    side_effect=[fake_api_process]
                ) as mock_popen:

                    start_fullstack()

                    # only API; no Popen attempted for a
                    # dev server whose dependencies failed to install
                    assert mock_popen.call_count == 1
