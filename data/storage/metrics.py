# -*- coding: utf-8 -*-

from data.storage.trades_repository import get_all_trades


def calculate_metrics(user_id):

    trades = get_all_trades(user_id)

    closed = [t for t in trades if t["status"] == "CLOSED"]

    total = len(closed)

    if total == 0:
        return {
            "total_trades": 0,
            "winrate": 0,
            "pnl": 0
        }

    wins = 0
    pnl_total = 0

    for t in closed:
        pnl_total += t["pnl"]
        if t["pnl"] > 0:
            wins += 1

    winrate = wins / total

    return {
        "total_trades": total,
        "winrate": round(winrate, 2),
        "pnl": round(pnl_total, 2)
    }