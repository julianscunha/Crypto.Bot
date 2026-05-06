# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path


DB_PATH = Path("data/storage/trades.db")


def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    # =====================================================
    # TRADES
    # =====================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,
        symbol TEXT,

        action TEXT,

        entry_price REAL,
        current_price REAL,

        quantity REAL,

        stop_loss REAL,
        take_profit REAL,

        trailing_stop REAL,

        breakeven_enabled INTEGER,

        status TEXT,

        pnl REAL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # =====================================================
    # EQUITY CURVE
    # =====================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equity_curve (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,

        equity REAL,
        realized_pnl REAL,
        unrealized_pnl REAL,

        drawdown REAL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    conn.close()