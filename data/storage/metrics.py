# -*- coding: utf-8 -*-

from data.storage.database import get_connection

from data.storage.equity_repository import (
    insert_equity_snapshot,
    get_equity_curve,
    INITIAL_BALANCE
)


def calculate_metrics(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM trades
    WHERE user_id = ?
    AND status = 'CLOSED'
    """, (user_id,))

    trades = cursor.fetchall()

    conn.close()

    total_trades = len(trades)

    if total_trades == 0:

        return {
            "total_trades": 0,
            "winrate": 0,
            "pnl": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "max_drawdown": 0,
            "equity": INITIAL_BALANCE
        }

    pnl_values = [t["pnl"] for t in trades]

    wins = [p for p in pnl_values if p > 0]
    losses = [p for p in pnl_values if p <= 0]

    total_pnl = round(sum(pnl_values), 2)

    winrate = round(
        len(wins) / total_trades,
        2
    )

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    profit_factor = round(
        gross_profit / gross_loss,
        2
    ) if gross_loss > 0 else 0

    avg_win = round(
        sum(wins) / len(wins),
        2
    ) if wins else 0

    avg_loss = round(
        sum(losses) / len(losses),
        2
    ) if losses else 0

    # =====================================================
    # EQUITY CURVE
    # =====================================================

    equity = INITIAL_BALANCE

    peak = equity

    max_drawdown = 0

    for pnl in pnl_values:

        equity += pnl

        if equity > peak:
            peak = equity

        drawdown = peak - equity

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    current_equity = round(
        INITIAL_BALANCE + total_pnl,
        2
    )

    insert_equity_snapshot(
        user_id=user_id,

        equity=current_equity,

        realized_pnl=total_pnl,

        unrealized_pnl=0,

        drawdown=round(max_drawdown, 2)
    )

    return {
        "total_trades": total_trades,

        "winrate": winrate,

        "pnl": total_pnl,

        "profit_factor": profit_factor,

        "avg_win": avg_win,

        "avg_loss": avg_loss,

        "max_drawdown": round(max_drawdown, 2),

        "equity": current_equity
    }