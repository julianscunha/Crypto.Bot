# -*- coding: utf-8 -*-

from data.storage.database import get_connection


INITIAL_BALANCE = 10000.0


def insert_equity_snapshot(
    user_id,
    equity,
    realized_pnl,
    unrealized_pnl,
    drawdown
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO equity_curve (
        user_id,
        equity,
        realized_pnl,
        unrealized_pnl,
        drawdown
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        equity,
        realized_pnl,
        unrealized_pnl,
        drawdown
    ))

    conn.commit()

    conn.close()


def get_equity_curve(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM equity_curve
    WHERE user_id = ?
    ORDER BY id ASC
    """, (user_id,))

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_latest_equity(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM equity_curve
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()

    conn.close()

    return row