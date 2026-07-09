# -*- coding: utf-8 -*-

"""
Timestamped backup of data/storage/trades.db, with rotation.

Uses sqlite3's own backup API (Connection.backup()) instead of a
plain file copy -- trades.db runs in WAL mode (see
data/storage/database.py), where a straight filesystem copy of the
.db file alone can miss writes still sitting in the -wal file and
produce an inconsistent snapshot. The backup API talks to SQLite
directly and always produces a complete, consistent copy regardless
of WAL state, without requiring the Runner/API to be stopped first.

Usage:
    python scripts/backup_db.py [--keep N]

Intended to be run manually or wired into the OS's own scheduler
(cron, Task Scheduler) -- this project has no built-in scheduler of
its own.
"""

import argparse

import sqlite3

import sys

from datetime import datetime

from pathlib import Path


ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

SOURCE_DB = (
    ROOT_DIR / "data" / "storage" / "trades.db"
)

BACKUP_DIR = (
    ROOT_DIR / "data" / "storage" / "backups"
)

DEFAULT_KEEP = 10


def create_backup(
    source_db: Path = SOURCE_DB,
    backup_dir: Path = BACKUP_DIR
) -> Path | None:

    if not source_db.exists():

        print(
            f"Nenhum banco encontrado em {source_db} -- nada para "
            "fazer backup."
        )

        return None

    backup_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = (
        datetime.now()
        .strftime("%Y%m%d_%H%M%S")
    )

    dest_path = (
        backup_dir / f"trades_{timestamp}.db"
    )

    source_conn = sqlite3.connect(str(source_db))

    dest_conn = sqlite3.connect(str(dest_path))

    try:

        source_conn.backup(
            dest_conn
        )

    finally:

        dest_conn.close()
        source_conn.close()

    print(f"Backup criado: {dest_path}")

    return dest_path


def rotate_backups(
    backup_dir: Path = BACKUP_DIR,
    keep: int = DEFAULT_KEEP
) -> None:

    backups = sorted(
        backup_dir.glob("trades_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    for stale_backup in backups[keep:]:

        stale_backup.unlink()

        print(f"Backup antigo removido: {stale_backup}")


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Cria um backup timestamped de data/storage/trades.db "
            "e remove backups antigos além do limite configurado."
        )
    )

    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        help=(
            "Quantos backups mais recentes manter "
            f"(padrão: {DEFAULT_KEEP})"
        )
    )

    args = parser.parse_args()

    dest_path = create_backup()

    if dest_path is None:
        return 1

    rotate_backups(
        keep=args.keep
    )

    return 0


if __name__ == "__main__":

    sys.exit(
        main()
    )
