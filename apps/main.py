# -*- coding: utf-8 -*-

import sys
import time
import asyncio
import multiprocessing
from core.config.env_bootstrap import bootstrap_environment

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)

# =========================================================
# GLOBAL WINDOWS FIX
# =========================================================

init(
    autoreset=True,
    wrap=True
)

sys.stdout.reconfigure(
    encoding="utf-8"
)


# =========================================================
# API
# =========================================================

def run_api():

    from colorama import init

    init(
        autoreset=True,
        wrap=True
    )

    import sys

    sys.stdout.reconfigure(
        encoding="utf-8"
    )

    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning"
    )


# =========================================================
# TRADER
# =========================================================

def run_trader():

    from colorama import init

    init(
        autoreset=True,
        wrap=True
    )

    import sys

    sys.stdout.reconfigure(
        encoding="utf-8"
    )

    from apps.trader.runner import (
        main as trader_main
    )

    asyncio.run(
        trader_main()
    )


# =========================================================
# TERMINATION
# =========================================================

def terminate_process(
    proc: multiprocessing.Process,
    name: str
):

    if proc.is_alive():

        print(
            f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
            f"Stopping {name}...",
            flush=True
        )

        proc.terminate()

        proc.join(timeout=5)

        if proc.is_alive():

            print(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"Force killing {name}...",
                flush=True
            )

            proc.kill()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print()

    print(
        Fore.LIGHTWHITE_EX +
        "=" * 60
    )

    print(
        Fore.LIGHTWHITE_EX +
        "               CRYPTO.BOT - FULL SYSTEM"
    )

    print(
        Fore.LIGHTWHITE_EX +
        "=" * 60
    )

    print()

    print(
        f"{Fore.GREEN}[BOOT]{Style.RESET_ALL} "
        f"Initializing API..."
    )
    
    bootstrap_environment()

    api_process = multiprocessing.Process(
        target=run_api
    )

    api_process.start()

    time.sleep(1)

    print(
        f"{Fore.GREEN}[BOOT]{Style.RESET_ALL} "
        f"Initializing TRADER..."
    )

    trader_process = multiprocessing.Process(
        target=run_trader
    )

    print()

    print(
        f"{Fore.GREEN}[OK]{Style.RESET_ALL} "
        f"API      -> http://127.0.0.1:8000"
    )

    print(
        f"{Fore.GREEN}[OK]{Style.RESET_ALL} "
        f"TRADER   -> RUNNING"
    )

    print(
        f"{Fore.GREEN}[OK]{Style.RESET_ALL} "
        f"MODE     -> PAPER"
    )

    print()

    print(
        Fore.LIGHTWHITE_EX +
        "=" * 60
    )

    print()

    trader_process.start()


    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        print()

        print(
            f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
            f"CTRL+C detected. Shutting down...",
            flush=True
        )

        terminate_process(
            api_process,
            "API"
        )

        terminate_process(
            trader_process,
            "TRADER"
        )

        print()

        print(
            f"{Fore.GREEN}[OK]{Style.RESET_ALL} "
            f"Shutdown complete",
            flush=True
        )

        sys.exit(0)