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

ROOT = Path(__file__).resolve().parent.parent.parent

# =====================================================
# STATUS LINE
# =====================================================

def status_line(label, value):

    return f"{label:.<30} {value}"

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

    print("")
    print("[0] Exit")
    print("")

# =====================================================
# RUN PROCESS
# =====================================================

def run_process(command, cwd=None):

    try:

        subprocess.run(
            command,
            cwd=cwd
        )

    except Exception as error:

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
# START RUNNER
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
# START OPTIMIZER
# =====================================================

def start_optimizer():

    run_process(
        [
            sys.executable,
            "-m",
            "apps.optimizer.optimizer"
        ]
    )

# =====================================================
# START BACKTEST
# =====================================================

def start_backtest():

    run_process(
        [
            sys.executable,
            "-m",
            "apps.backtest.backtest"
        ]
    )

# =====================================================
# START FRONTEND
# =====================================================

def start_frontend():

    run_process(
        [
            "npm",
            "run",
            "dev"
        ],
        cwd=str(ROOT / "frontend")
    )

# =====================================================
# START FULL STACK
# =====================================================

def start_fullstack():

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "apps.trader.runner"
        ]
    )

    subprocess.run(
        [
            "npm",
            "run",
            "dev"
        ],
        cwd=str(ROOT / "frontend")
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

            option = input("Select mode: ")

        except KeyboardInterrupt:

            print("")

            log(
                "SYSTEM",
                status_line(
                    "Shutdown",
                    "OK"
                ),
                "SUCCESS"
            )

            return

        if option == "1":

            start_runner()
            break

        elif option == "2":

            start_optimizer()
            break

        elif option == "3":

            start_backtest()
            break

        elif option == "4":

            start_frontend()
            break

        elif option == "5":

            start_fullstack()
            break

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