# -*- coding: utf-8 -*-

"""
Regression test for the missing alembic migration bug.

Bug fixed: highest_price, lowest_price, unrealized_pnl, and
realized_pnl exist as columns in the shipped trades.db but were never
added by any tracked alembic migration. Running `alembic upgrade head`
against a brand new database produced a `trades` table missing these
4 columns, which PositionLifecycleService, the ORM model, and the API
all depend on. A new migration (add_position_lifecycle_columns) closes
this gap.

This test runs the real alembic migration chain end-to-end against an
isolated temp sqlite file -- it does not use the shared test-session
engine from conftest.py, since the point is to validate the migration
scripts themselves, independent of the ORM's create_all() shortcut.
"""

import os

import sqlite3

import tempfile

from alembic import command

from alembic.config import Config


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)


def _run_alembic_upgrade(db_path):

    config = Config(
        os.path.join(
            PROJECT_ROOT,
            "alembic.ini"
        )
    )

    config.set_main_option(
        "script_location",
        os.path.join(
            PROJECT_ROOT,
            "alembic"
        )
    )

    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{db_path}"
    )

    command.upgrade(
        config,
        "head"
    )


class TestAlembicMigrationChain:

    def test_upgrade_head_creates_all_trades_columns(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            db_path = os.path.join(
                tmp_dir,
                "migration_test.db"
            )

            _run_alembic_upgrade(db_path)

            conn = sqlite3.connect(db_path)

            cursor = conn.cursor()

            cursor.execute(
                "PRAGMA table_info(trades)"
            )

            columns = {
                row[1]
                for row in cursor.fetchall()
            }

            conn.close()

            for expected in (
                "highest_price",
                "lowest_price",
                "unrealized_pnl",
                "realized_pnl",
                "exit_reason",
                "breakeven_enabled",
                "created_at"
            ):

                assert expected in columns, (
                    f"Column '{expected}' missing after "
                    "alembic upgrade head"
                )

    def test_upgrade_head_creates_all_tables(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            db_path = os.path.join(
                tmp_dir,
                "migration_test_tables.db"
            )

            _run_alembic_upgrade(db_path)

            conn = sqlite3.connect(db_path)

            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )

            tables = {
                row[0]
                for row in cursor.fetchall()
            }

            conn.close()

            for expected in (
                "trades",
                "equity_curve",
                "portfolio_snapshots"
            ):

                assert expected in tables
