# -*- coding: utf-8 -*-

"""
Global pytest fixtures.

CRITICAL: redirects the SQLAlchemy engine/session factory to an
isolated, temporary SQLite file for the entire test session, so
that running the test suite NEVER reads or writes the real
data/storage/trades.db used by the live paper-trading bot.

`SessionLocal` is reconfigured in place (sessionmaker.configure)
rather than rebound, because several modules already did
`from data.storage.database import SessionLocal` at import time;
rebinding the module-level name would not affect those references,
but mutating the existing factory's bind affects every reference to it.
"""

import os

import tempfile

from pathlib import Path

import pytest

from sqlalchemy import create_engine


@pytest.fixture(scope="session", autouse=True)
def _isolated_test_logs():

    """
    core/utils/console_logger.py resolves RUNTIME_LOG_FILE and
    ERROR_LOG_FILE at import time, relative to the real project
    root, and writes to them on every log() call. Without this
    fixture, running the test suite pollutes the real logs/
    directory the user actually reads. Redirect both file handlers
    to an isolated temp directory for the whole test session.
    """

    import logging

    from logging.handlers import RotatingFileHandler

    from core.utils import console_logger

    tmp_dir = tempfile.mkdtemp(
        prefix="crypto_bot_test_logs_"
    )

    for logger_name, filename in (
        ("runtime_logger", "test_runtime.log"),
        ("error_logger", "test_errors.log")
    ):

        logger = logging.getLogger(logger_name)

        logger.handlers.clear()

        handler = RotatingFileHandler(

            os.path.join(tmp_dir, filename),

            maxBytes=10_000_000,

            backupCount=1,

            encoding="utf-8"
        )

        handler.setFormatter(
            logging.Formatter(
                "%(message)s"
            )
        )

        logger.addHandler(handler)

    yield


@pytest.fixture(scope="session", autouse=True)
def _isolated_settings_env():

    """
    core/config/settings_repository.py resolves ENV_PATH at import
    time, pointing at the real project .env file. Redirect it to an
    isolated temp file for the whole test session so tests never
    read or write the user's real Binance API credentials.
    """

    from core.config import settings_repository

    tmp_dir = tempfile.mkdtemp(
        prefix="crypto_bot_test_env_"
    )

    fake_env_path = Path(
        tmp_dir
    ) / ".env"

    fake_env_path.write_text(
        "MODE=paper\n"
        "BINANCE_TESTNET=true\n"
        "BINANCE_API_KEY=\n"
        "BINANCE_SECRET_KEY=\n"
    )

    settings_repository.ENV_PATH = (
        fake_env_path
    )

    yield fake_env_path


@pytest.fixture(scope="session", autouse=True)
def _isolated_test_database():

    from data.storage import database as database_module

    tmp_dir = tempfile.mkdtemp(
        prefix="crypto_bot_test_db_"
    )

    tmp_db_path = os.path.join(
        tmp_dir,
        "test_trades.db"
    )

    test_engine = create_engine(

        f"sqlite:///{tmp_db_path}",

        connect_args={
            "check_same_thread": False
        },

        future=True
    )

    # =====================================================
    # REBIND ENGINE + SESSION FACTORY IN PLACE
    # =====================================================

    database_module.engine = test_engine

    database_module.SessionLocal.configure(
        bind=test_engine
    )

    # =====================================================
    # CREATE SCHEMA
    # =====================================================

    from data.storage import models  # noqa: F401 (registers tables on Base)

    database_module.Base.metadata.create_all(
        bind=test_engine
    )

    yield test_engine

    test_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():

    """
    Truncate all tables before every test so tests don't leak
    state into one another, without ever touching the real DB.
    """

    from data.storage.repositories.trades_repository import (
        trades_repository
    )

    from data.storage.repositories.portfolio_repository import (
        portfolio_repository
    )

    from core.state.market_state import market_state

    trades_repository.reset_all()

    portfolio_repository.reset_all()

    # market_state is a module-level singleton that accumulates
    # blocked_signal_reasons across calls -- without resetting it
    # between tests, a blocked signal registered by one test leaks
    # into assertions made by a later test that expects a clean slate
    market_state.blocked_signal_reasons.clear()

    market_state.execution_reasons.clear()

    yield
