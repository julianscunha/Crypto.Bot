# -*- coding: utf-8 -*-

from data.storage.database import get_connection


def open_position(user_id, action, price, quantity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (user_id, action, price, quantity, status, pnl)
    VALUES (?, ?, ?, ?, 'OPEN', 0)
    """, (user_id, action, price, quantity))

    conn.commit()
    conn.close()


def get_open_position(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM trades
    WHERE user_id = ? AND status = 'OPEN'
    ORDER BY id DESC LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    return row


def close_position(position_id, pnl):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET status = 'CLOSED', pnl = ?
    WHERE id = ?
    """, (pnl, position_id))

    conn.commit()
    conn.close()