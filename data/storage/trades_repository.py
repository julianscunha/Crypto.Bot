# -*- coding: utf-8 -*-

from data.storage.database import get_connection


def create_trade(user_id, action, price, quantity, status="OPEN", pnl=0.0):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (user_id, action, price, quantity, status, pnl)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, action, price, quantity, status, pnl))

    conn.commit()
    conn.close()


def get_all_trades(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM trades WHERE user_id = ?
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return rows