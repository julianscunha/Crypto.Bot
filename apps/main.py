# -*- coding: utf-8 -*-

import sys
import time
import asyncio
import multiprocessing

from colorama import Fore, Style, init

# === FIX GLOBAL WINDOWS ===
init(autoreset=True, wrap=True)
sys.stdout.reconfigure(encoding="utf-8")


def run_api():
    from colorama import init
    init(autoreset=True, wrap=True)

    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )


def run_trader():
    from colorama import init
    init(autoreset=True, wrap=True)

    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    from apps.trader.runner import main as trader_main

    asyncio.run(trader_main())


def terminate_process(proc: multiprocessing.Process, name: str):
    if proc.is_alive():
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Stopping {name}...", flush=True)
        proc.terminate()
        proc.join(timeout=5)

        if proc.is_alive():
            print(f"{Fore.RED}[WARN]{Style.RESET_ALL} Force killing {name}...", flush=True)
            proc.kill()


if __name__ == "__main__":

    api_process = multiprocessing.Process(target=run_api)
    trader_process = multiprocessing.Process(target=run_trader)

    api_process.start()
    trader_process.start()

    print("==========================================")
    print("       CRYPTO.BOT - FULL SYSTEM")
    print("==========================================")
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} API + TRADER running", flush=True)
    print()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[INFO]{Style.RESET_ALL} CTRL+C detected. Shutting down...", flush=True)

        terminate_process(api_process, "API")
        terminate_process(trader_process, "TRADER")

        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Shutdown complete", flush=True)
        sys.exit(0)