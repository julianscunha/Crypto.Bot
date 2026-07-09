# -*- coding: utf-8 -*-

"""
Unit tests for scripts/backup_db.py
"""

import sqlite3

import time

from pathlib import Path

import pytest

from scripts.backup_db import (
    create_backup,
    rotate_backups
)


@pytest.fixture
def source_db(tmp_path) -> Path:

    db_path = tmp_path / "trades.db"

    conn = sqlite3.connect(str(db_path))

    conn.execute(
        "CREATE TABLE trades (id INTEGER PRIMARY KEY, symbol TEXT)"
    )

    conn.execute(
        "INSERT INTO trades (symbol) VALUES ('BTCUSDT')"
    )

    conn.commit()

    conn.close()

    return db_path


@pytest.fixture
def backup_dir(tmp_path) -> Path:

    return tmp_path / "backups"


class TestCreateBackup:

    def test_returns_none_when_source_missing(
        self,
        tmp_path,
        backup_dir
    ):

        missing_db = tmp_path / "does_not_exist.db"

        result = create_backup(
            source_db=missing_db,
            backup_dir=backup_dir
        )

        assert result is None

    def test_creates_a_consistent_copy_of_the_source(
        self,
        source_db,
        backup_dir
    ):

        result = create_backup(
            source_db=source_db,
            backup_dir=backup_dir
        )

        assert result is not None

        assert result.exists()

        conn = sqlite3.connect(str(result))

        rows = conn.execute(
            "SELECT symbol FROM trades"
        ).fetchall()

        conn.close()

        assert rows == [("BTCUSDT",)]

    def test_backup_filename_is_timestamped(
        self,
        source_db,
        backup_dir
    ):

        result = create_backup(
            source_db=source_db,
            backup_dir=backup_dir
        )

        assert result.name.startswith("trades_")

        assert result.name.endswith(".db")


class TestRotateBackups:

    def test_keeps_only_the_n_most_recent_backups(
        self,
        source_db,
        backup_dir
    ):

        for _ in range(5):

            create_backup(
                source_db=source_db,
                backup_dir=backup_dir
            )

            # filenames are second-precision timestamps -- force
            # distinct names so rotation has something meaningful to
            # sort by instead of every backup overwriting the last
            time.sleep(1.05)

        assert len(
            list(backup_dir.glob("trades_*.db"))
        ) == 5

        rotate_backups(
            backup_dir=backup_dir,
            keep=2
        )

        remaining = sorted(
            backup_dir.glob("trades_*.db")
        )

        assert len(remaining) == 2

    def test_keeping_more_than_exist_removes_nothing(
        self,
        source_db,
        backup_dir
    ):

        create_backup(
            source_db=source_db,
            backup_dir=backup_dir
        )

        rotate_backups(
            backup_dir=backup_dir,
            keep=10
        )

        assert len(
            list(backup_dir.glob("trades_*.db"))
        ) == 1
