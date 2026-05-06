# -*- coding: utf-8 -*-

from data.storage.database import get_connection


def open_position(
    user_id,
    symbol,
    action,
    entry_price,
    quantity,
    stop_loss,
    take_profit,
    trailing_stop,
    breakeven_enabled
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (
        user_id,
        symbol,
        action,
        entry_price,
        current_price,
        quantity,
        stop_loss,
        take_profit,
        trailing_stop,
        breakeven_enabled,
        status,
        pnl
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0)
    """, (
        user_id,
        symbol,
        action,
        entry_price,
        entry_price,
        quantity,
        stop_loss,
        take_profit,
        trailing_stop,
        int(breakeven_enabled)
    ))

    conn.commit()

    conn.close()


def get_open_position(user_id, symbol):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM trades
    WHERE user_id = ?
    AND symbol = ?
    AND status = 'OPEN'
    ORDER BY id DESC
    LIMIT 1
    """, (
        user_id,
        symbol
    ))

    row = cursor.fetchone()

    conn.close()

    return row


def update_position(
    position_id,
    current_price,
    stop_loss,
    trailing_stop,
    breakeven_enabled
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET current_price = ?,
        stop_loss = ?,
        trailing_stop = ?,
        breakeven_enabled = ?
    WHERE id = ?
    """, (
        current_price,
        stop_loss,
        trailing_stop,
        int(breakeven_enabled),
        position_id
    ))

    conn.commit()

    conn.close()


def close_position(position_id, pnl):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET status = 'CLOSED',
        pnl = ?
    WHERE id = ?
    """, (
        pnl,
        position_id
    ))

    conn.commit()

    conn.close()