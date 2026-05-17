# -*- coding: utf-8 -*-

import subprocess
import sys

from pathlib import Path

from core.utils.console_logger import (
    log,
    print_section
)

from scripts.bootstrap.validate import (
    validate_environment
)

from scripts.bootstrap.bootstrap import (
    install_requirements
)

from scripts.bootstrap.process_manager import (
    cleanup_old_processes
)

# =====================================================
# ROOT
# =====================================================

ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

# =====================================================
# STATUS LINE
# =====================================================

def status_line(
    label,
    value
):

    return (
        f"{label:.<30} {value}"
    )

# =====================================================
# MENU
# =====================================================

def show_menu():

    print_section(
        "RUNTIME MENU"
    )

    print("[1] Runner")
    print("[2] Optimizer")
    print("[3] Backtest")
    print("[4] Frontend")
    print("[5] Full Stack")

    print()

    print("[0] Exit")

    print()

# =====================================================
# SAFE TERMINATION
# =====================================================

def terminate_process(
    process
):

    if not process:

        return

    try:

        process.terminate()

        process.wait(
            timeout=5
        )

    except Exception:

        try:

            process.kill()

        except Exception:

            pass

# =====================================================
# RUN PROCESS
# =====================================================

def run_process(
    command,
    cwd=None
):

    process = None

    try:

        process = subprocess.Popen(
            command,
            cwd=cwd
        )

        process.wait()

    except KeyboardInterrupt:

        print()

        log(
            "SYSTEM",
            status_line(
                "Shutdown",
                "OK"
            ),
            "SUCCESS"
        )

        terminate_process(
            process
        )

    except Exception as error:

        terminate_process(
            process
        )

        with open(
            ROOT / "logs" / "errors.log",
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"{str(error)}\n"
            )

        log(
            "SYSTEM",
            status_line(
                "Runtime",
                "FAILED"
            ),
            "ERROR"
        )

# =====================================================
# RUNNER
# =====================================================

def start_runner():

    run_process(
        [
            sys.executable,
            "-m",
            "apps.trader.runner"
        ]
    )

# =====================================================
# OPTIMIZER
# =====================================================

def start_optimizer():

    run_process(
        [
            sys.executable,
            "-m",
            "backtest.optimizer.optimizer_engine"
        ]
    )

# =====================================================
# BACKTEST
# =====================================================

def start_backtest():

    run_process(
        [
            sys.executable,
            "-m",
            "backtest.runner"
        ]
    )

# =====================================================
# FRONTEND
# =====================================================

def start_frontend():

    run_process(
        [
            "npm",
            "run",
            "dev"
        ],
        cwd=str(
            ROOT / "frontend"
        )
    )

# =====================================================
# FULL STACK
# =====================================================

def start_fullstack():

    runner_process = None

    frontend_process = None

    try:

        runner_process = (
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "apps.trader.runner"
                ]
            )
        )

        frontend_process = (
            subprocess.Popen(
                [
                    "npm",
                    "run",
                    "dev"
                ],
                cwd=str(
                    ROOT / "frontend"
                )
            )
        )

        frontend_process.wait()

    except KeyboardInterrupt:

        print()

        log(
            "SYSTEM",
            status_line(
                "Shutdown",
                "OK"
            ),
            "SUCCESS"
        )

    finally:

        terminate_process(
            runner_process
        )

        terminate_process(
            frontend_process
        )

# =====================================================
# MAIN
# =====================================================

def main():

    cleanup_old_processes()

    if not validate_environment():

        return

    if not install_requirements():

        return

    while True:

        show_menu()

        try:

            option = input(
                "Select mode: "
            )

        except KeyboardInterrupt:

            print()

            log(
                "SYSTEM",
                status_line(
                    "Shutdown",
                    "OK"
                ),
                "SUCCESS"
            )

            return

        # =================================================
        # RUNNER
        # =================================================

        if option == "1":

            start_runner()

            break

        # =================================================
        # OPTIMIZER
        # =================================================

        elif option == "2":

            start_optimizer()

            break

        # =================================================
        # BACKTEST
        # =================================================

        elif option == "3":

            start_backtest()

            break

        # =================================================
        # FRONTEND
        # =================================================

        elif option == "4":

            start_frontend()

            break

        # =================================================
        # FULL STACK
        # =================================================

        elif option == "5":

            start_fullstack()

            break

        # =================================================
        # EXIT
        # =================================================

        elif option == "0":

            log(
                "SYSTEM",
                status_line(
                    "Shutdown",
                    "OK"
                ),
                "SUCCESS"
            )

            return

        # =================================================
        # INVALID OPTION
        # =================================================

        else:

            log(
                "SYSTEM",
                status_line(
                    "Invalid Option",
                    "WARNING"
                ),
                "WARNING"
            )

# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    main()