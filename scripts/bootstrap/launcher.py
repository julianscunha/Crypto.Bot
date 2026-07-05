# -*- coding: utf-8 -*-

import subprocess
import sys
import shutil

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

    from core.config.settings import settings
    from core.config.trading_config import TRADING_CONFIG

    mode    = settings.MODE.upper()
    testnet = getattr(settings, "BINANCE_TESTNET", True)
    mode_label = f"LIVE {'TESTNET' if testnet else 'MAINNET'}" if mode == "LIVE" else "PAPER (simulado)"

    balance = TRADING_CONFIG.get("account_balance", "?")
    risk    = TRADING_CONFIG.get("risk_per_trade_percent", "?")
    rr_min  = TRADING_CONFIG.get("minimum_risk_reward_ratio", "?")
    max_pos = getattr(settings, "MAX_OPEN_POSITIONS", "?")
    symbols = " · ".join(settings.SYMBOLS)
    tf      = settings.KLINE_INTERVAL

    print_section("CONFIGURAÇÃO ATIVA")
    print(f"  Modo .............. {mode_label}")
    print(f"  Pares ............. {symbols}")
    print(f"  Timeframe ......... {tf}")
    print(f"  Saldo ............. ${balance}")
    print(f"  Risco/trade ....... {risk}%")
    print(f"  Risco/retorno min . {rr_min}")
    print(f"  Máx. posições ..... {max_pos}")
    print()

    print_section("RUNTIME MENU")
    print("[1] Runner       → inicia o bot de trading")
    print("[2] Optimizer    → calibra TP/SL com dados reais da Binance")
    print("[3] Backtest     → valida estratégia sobre histórico")
    print("[4] Frontend     → painel web (http://localhost:5173)")
    print("[5] Full Stack   → API + Frontend (bot inicia pela web)")
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

        (ROOT / "logs").mkdir(
            parents=True,

            exist_ok=True
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
# FRONTEND AVAILABILITY
# =====================================================
#
# There is no frontend/ directory in this project yet -- per
# README_FULL.md's roadmap, "frontend operational dashboard" is
# listed under upcoming modules, not something already built.
# Calling `npm run dev` with cwd=frontend/ before it exists raises
# FileNotFoundError. Guard for it explicitly with a clear message
# instead of letting that crash propagate uncaught.

def frontend_available():

    return (
        ROOT / "frontend"
    ).exists()


def warn_frontend_unavailable():

    log(
        "SYSTEM",
        status_line(
            "Frontend",
            "NOT_FOUND"
        ),
        "WARNING"
    )

    log(
        "SYSTEM",
        (
            "No frontend/ directory found. "
            "The dashboard frontend is on the roadmap "
            "(see README_FULL.md) but not built yet. "
            "Use the API at http://127.0.0.1:8000 "
            "directly, or run option [1] Runner."
        ),
        "WARNING"
    )

# =====================================================
# NPM RESOLUTION
# =====================================================
#
# On Windows, npm is actually npm.cmd (a batch script), and
# subprocess.Popen(["npm", ...]) without shell=True raises
# FileNotFoundError ([WinError 2]) because CreateProcess doesn't
# resolve PATHEXT extensions the way a shell does. shutil.which()
# finds the correct executable (npm.cmd on Windows, npm on
# Linux/macOS) without needing shell=True, which would otherwise
# require careful argument escaping.

def resolve_npm_command():

    npm_path = shutil.which(
        "npm"
    )

    if npm_path is None:

        return None

    return [
        npm_path,
        "run",
        "dev"
    ]


def warn_npm_not_found():

    log(
        "SYSTEM",
        status_line(
            "Frontend",
            "NPM_NOT_FOUND"
        ),
        "WARNING"
    )

    log(
        "SYSTEM",
        (
            "npm was not found on PATH. Install Node.js "
            "(https://nodejs.org) and restart this launcher, or run "
            "the frontend manually: cd frontend && npm run dev"
        ),
        "WARNING"
    )

# =====================================================
# FRONTEND DEPENDENCIES
# =====================================================
#
# node_modules/ is never shipped (it's large and reproducible), so
# a fresh checkout has frontend/ with no node_modules/ yet. Running
# `npm run dev` (which is really just `vite`) before `npm install`
# fails with "'vite' is not recognized..." -- this installs
# dependencies automatically the first time, the same way
# install_requirements() does for the Python side.

def frontend_dependencies_installed(
    npm_command
):

    return (
        ROOT / "frontend" / "node_modules"
    ).exists()


def install_frontend_dependencies(
    npm_path
):

    log(
        "SYSTEM",
        status_line(
            "Frontend deps",
            "INSTALLING"
        ),
        "WARNING"
    )

    result = subprocess.run(
        [
            npm_path,
            "install"
        ],
        cwd=str(
            ROOT / "frontend"
        )
    )

    if result.returncode != 0:

        log(
            "SYSTEM",
            status_line(
                "Frontend deps",
                "INSTALL_FAILED"
            ),
            "ERROR"
        )

        return False

    log(
        "SYSTEM",
        status_line(
            "Frontend deps",
            "INSTALLED"
        ),
        "SUCCESS"
    )

    return True

# =====================================================
# FRONTEND
# =====================================================

def start_frontend():

    if not frontend_available():

        warn_frontend_unavailable()

        return

    npm_command = resolve_npm_command()

    if npm_command is None:

        warn_npm_not_found()

        return

    if not frontend_dependencies_installed(npm_command):

        if not install_frontend_dependencies(npm_command[0]):

            return

    run_process(
        npm_command,
        cwd=str(
            ROOT / "frontend"
        )
    )

# =====================================================
# FULL STACK
# =====================================================
#
# "Full stack" currently means the two backend processes that
# actually exist: the API (apps.api.main, served via uvicorn) and
# the live paper-trading runner (apps.trader.runner). The frontend
# is included automatically once frontend/ exists, but its absence
# must never crash the API + Trader stack that IS available today.

def start_fullstack():

    api_process = None

    runner_process = None

    frontend_process = None

    try:

        api_process = (
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "apps.api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--log-level",
                    "warning"
                ]
            )
        )

        log(
            "SYSTEM",
            status_line(
                "API",
                "http://127.0.0.1:8000"
            ),
            "SUCCESS"
        )

        log(
            "SYSTEM",
            status_line(
                "Trader",
                "AGUARDANDO — inicie o bot pela interface web (▶)"
            ),
            "WARNING"
        )

        npm_command = (
            resolve_npm_command()
            if frontend_available()
            else None
        )

        frontend_ready = (
            npm_command is not None
            and (
                frontend_dependencies_installed(npm_command)
                or install_frontend_dependencies(npm_command[0])
            )
        )

        if not frontend_ready:

            if npm_command is None and frontend_available():

                warn_npm_not_found()

            elif not frontend_available():

                warn_frontend_unavailable()

            api_process.wait()

        else:

            frontend_process = (
                subprocess.Popen(
                    npm_command,
                    cwd=str(
                        ROOT / "frontend"
                    )
                )
            )

            log(
                "SYSTEM",
                status_line(
                    "Frontend",
                    "RUNNING"
                ),
                "SUCCESS"
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
            api_process
        )

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