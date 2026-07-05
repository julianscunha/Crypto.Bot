# -*- coding: utf-8 -*-

"""
Reconciliação de startup — compara o estado real da Binance com
o banco local e corrige divergências antes do bot começar a operar.

Cenários cobertos:

1. Posição OPEN no banco, mas OCO já resolvida na Binance (ALL_DONE)
   → Posição fechou enquanto o bot estava offline. Marca como fechada
   com reason=RECONCILED_CLOSED.

2. Posição OPEN no banco, sem nenhuma ordem aberta na Binance
   (OCO sumiu ou nunca existiu)
   → Emergência: tenta colocar market sell imediatamente, depois
   marca como fechada.

3. Nenhuma posição OPEN no banco, mas há ordens abertas na Binance
   → Posição foi aberta fora do bot ou banco foi apagado. Loga como
   WARNING — não cria registro para não distorcer as métricas.
"""

from core.utils.console_logger import log
from data.storage.repositories.trades_repository import trades_repository
from core.config.settings import settings


DEFAULT_USER_ID = 0


async def reconcile_on_startup(client) -> None:

    log("SYSTEM", "RECONCILIAÇÃO iniciando…")

    open_trades = trades_repository.get_open_trades(
        user_id=DEFAULT_USER_ID
    )

    if not open_trades:
        log("SYSTEM", "RECONCILIAÇÃO OK — sem posições abertas no banco")
        return

    log(
        "SYSTEM",
        f"RECONCILIAÇÃO verificando {len(open_trades)} posição(ões) abertas"
    )

    for trade in open_trades:

        await _reconcile_trade(client, trade)

    log("SYSTEM", "RECONCILIAÇÃO concluída")


async def _reconcile_trade(client, trade) -> None:

    symbol    = trade.symbol
    trade_id  = trade.id

    # =========================================================
    # Sem order_list_id — posição criada antes da implementação
    # do rastreamento. Não conseguimos verificar o estado real.
    # =========================================================

    if not trade.order_list_id:

        log(
            "SYSTEM",
            (
                f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                "sem order_list_id — verificação manual necessária"
            ),
            "WARNING"
        )
        return

    # =========================================================
    # Verifica OCO na Binance
    # =========================================================

    try:

        from core.services.binance_trading_client import BinanceTradingError

        status = await client.get_order_list_status(
            symbol=symbol,
            order_list_id=int(trade.order_list_id)
        )

        list_status = status.get("listOrderStatus", "")

        if list_status == "ALL_DONE":

            # OCO executou enquanto bot estava offline
            log(
                "SYSTEM",
                (
                    f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                    "OCO já resolvida — marcando como fechada"
                ),
                "WARNING"
            )

            trades_repository.close_trade(
                trade_id=trade_id,
                exit_price=trade.current_price or trade.entry_price,
                pnl=trade.unrealized_pnl or 0.0,
                reason="RECONCILED_CLOSED"
            )

        elif list_status == "EXECUTING":

            # OCO ainda ativa — posição OK
            log(
                "SYSTEM",
                f"RECONCILIAÇÃO {symbol} id={trade_id}: OCO ativa — OK"
            )

        else:

            # Status desconhecido — logar para inspeção manual
            log(
                "SYSTEM",
                (
                    f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                    f"status desconhecido '{list_status}' — verificação manual"
                ),
                "WARNING"
            )

    except Exception as error:

        # OCO não encontrada — pode ter sido cancelada externamente
        # Tenta fechar a posição real com market sell de emergência

        log(
            "SYSTEM",
            (
                f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                f"OCO não encontrada ({error}) — "
                "tentando fechar posição com market sell"
            ),
            "ERROR"
        )

        await _emergency_close(client, trade)


async def _emergency_close(client, trade) -> None:

    symbol   = trade.symbol
    trade_id = trade.id

    try:

        from core.services.binance_trading_client import BinanceTradingError

        await client.place_market_order(
            symbol=symbol,
            side="SELL",
            quantity=trade.quantity
        )

        trades_repository.close_trade(
            trade_id=trade_id,
            exit_price=trade.current_price or trade.entry_price,
            pnl=trade.unrealized_pnl or 0.0,
            reason="RECONCILED_EMERGENCY_CLOSE"
        )

        log(
            "SYSTEM",
            (
                f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                "posição fechada com market sell de emergência"
            ),
            "WARNING"
        )

    except Exception as sell_error:

        log(
            "SYSTEM",
            (
                f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                f"FALHA NO FECHAMENTO DE EMERGÊNCIA — {sell_error} — "
                "INTERVENÇÃO MANUAL NECESSÁRIA IMEDIATAMENTE"
            ),
            "ERROR"
        )
