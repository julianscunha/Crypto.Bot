from pathlib import Path
from dotenv import load_dotenv
import os
import shutil
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE_FILE = ROOT_DIR / ".env.example"


REQUIRED_VARS = [
    "BINANCE_API_KEY",
    "BINANCE_SECRET_KEY",
    "MODE",
]


def ensure_env_file() -> None:
    """
    Creates .env automatically from .env.example
    if it does not exist.
    """

    if ENV_FILE.exists():
        return

    if not ENV_EXAMPLE_FILE.exists():
        raise FileNotFoundError(
            ".env.example not found in project root."
        )

    print("[BOOT] .env not found")
    print("[BOOT] Creating .env from .env.example")

    shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)

    print("[OK] .env created successfully")


def load_environment() -> None:
    """
    Loads environment variables from .env
    """

    load_dotenv(dotenv_path=ENV_FILE)


def validate_environment() -> None:
    """
    Validates required environment variables.
    """

    missing = []

    for key in REQUIRED_VARS:
        value = os.getenv(key)

        if value is None or value.strip() == "":
            missing.append(key)

    if missing:
        print("\n[ERROR] Missing required environment variables:\n")

        for item in missing:
            print(f" - {item}")

        print("\nPlease update your .env file.\n")

        sys.exit(1)

    print("[OK] Environment variables loaded")


def bootstrap_environment() -> None:
    """
    Full environment bootstrap flow.
    """

    ensure_env_file()
    load_environment()
    validate_environment()
