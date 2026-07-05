# -*- coding: utf-8 -*-

"""
Direct tests for data/storage/database.py's SQLite PRAGMA event
listener, which is registered against the module-level `engine`
object specifically (not whatever engine conftest.py's
_isolated_test_database fixture swaps SessionLocal to), so it needs
its own dedicated exercise to get covered.
"""

import sqlite3

import tempfile

import os

from sqlalchemy import create_engine, event

from data.storage import database as database_module


class TestSqlitePragmaListener:

    def test_pragma_listener_applies_settings_on_connect(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            db_path = os.path.join(
                tmp_dir,
                "pragma_test.db"
            )

            test_engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={
                    "check_same_thread": False
                },
                future=True
            )

            # re-register the exact same listener function this
            # module defines, against our throwaway engine, so we
            # exercise the real function body directly
            event.listens_for(
                test_engine,
                "connect"
            )(
                database_module.set_sqlite_pragma
            )

            connection = test_engine.connect()

            raw_connection = (
                connection.connection
            )

            cursor = raw_connection.cursor()

            cursor.execute("PRAGMA journal_mode;")

            journal_mode = cursor.fetchone()[0]

            cursor.execute("PRAGMA foreign_keys;")

            foreign_keys = cursor.fetchone()[0]

            connection.close()

            test_engine.dispose()

            assert journal_mode.lower() == "wal"

            assert foreign_keys == 1


class TestInitDb:

    def test_init_db_is_idempotent(self):

        # calling it twice in a row must not raise
        database_module.init_db()

        database_module.init_db()

    def test_init_db_imports_and_registers_models(self):

        database_module.init_db()

        table_names = set(
            database_module.Base.metadata.tables.keys()
        )

        assert "trades" in table_names

        assert "equity_curve" in table_names

        assert "portfolio_snapshots" in table_names
