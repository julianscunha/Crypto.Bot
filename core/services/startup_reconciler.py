# -*- coding: utf-8 -*-

"""
Reconciliação de startup — compara o estado real da Binance com
o banco local e corrige divergências antes do bot começar a operar.

Cenários cobertos:

1. Posição OPEN no banco, mas OCO já resolvida na Binance (ALL_DONE)
   → Posição fechou enquanto o bot estava offline. Marca como fechada
   com reason=RECONCILED_CLOSED.

2. Posição OPEN no banco, sem nenhuma ordem aberta na Binance
   (a Binance confirma explicitamente que a OCO não existe — código
   -2013 "Order does not exist")
   → Emergência: tenta colocar market sell imediatamente, depois
   marca como fechada. Qualquer outro erro (rede, auth, timeout) NÃO
   aciona esse fechamento automático — o estado real é desconhecido,
   e agir às cegas é mais arriscado que alertar o operador.

3. Nenhuma posição OPEN no banco, mas há ordens abertas na Binance
   → Posição foi aberta fora do bot ou o banco foi apagado/perdido.
   Loga CRITICAL — não cria registro para não distorcer as métricas,
   mas não fecha/cancela nada automaticamente (estado desconhecido).

Trades sem `order_list_id` (criados antes do rastreamento de ordens
existir) não podem ser verificados contra a Binance — também logam
CRITICAL, já que representam uma posição real potencialmente sem
proteção que a reconciliação não consegue confirmar.

Todo ponto CRITICAL aqui é um gancho para o alerta externo (webhook)
que a Fase 2 do roadmap adiciona em core/services/alert_service.py —
por ora, esses pontos só logam localmente.
"""

from core.services.binance_trading_client import BinanceTradingError
from core.utils.console_logger import log
from data.storage.repositories.trades_repository import trades_repository


DEFAULT_USER_ID = 0

# Binance error code for "Order does not exist" -- the only case where
# we can be confident the OCO is genuinely gone rather than the
# request itself having failed for an unrelated reason.
ORDER_NOT_FOUND_CODE = -2013


async def reconcile_on_startup(client, symbols: list[str] | None = None) -> None:

    log("SYSTEM", "RECONCILIAÇÃO iniciando…")

    open_trades = trades_repository.get_open_trades(
        user_id=DEFAULT_USER_ID
    )

    if not open_trades:
        log("SYSTEM", "RECONCILIAÇÃO OK — sem posições abertas no banco")

    else:

        log(
            "SYSTEM",
            f"RECONCILIAÇÃO verificando {len(open_trades)} posição(ões) abertas"
        )

        for trade in open_trades:

            await _reconcile_trade(client, trade)

    await _reconcile_orphan_orders(client, open_trades, symbols)

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
                "sem order_list_id — posição real sem verificação "
                "possível contra a Binance — INTERVENÇÃO MANUAL NECESSÁRIA"
            ),
            "CRITICAL"
        )
        return

    # =========================================================
    # Verifica OCO na Binance
    # =========================================================

    try:
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

    except BinanceTradingError as error:

        if error.binance_code == ORDER_NOT_FOUND_CODE:

            # A Binance confirma explicitamente que a OCO não existe
            # mais — só nesse caso é seguro assumir que a posição
            # ficou desprotegida e tentar o fechamento de emergência.

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

            return

        # Qualquer outro erro (rede, auth, timeout, erro inesperado da
        # Binance) não permite concluir que a OCO sumiu -- o estado
        # real é desconhecido. Fechar automaticamente aqui poderia
        # duplicar/cancelar uma proteção que na verdade ainda existe.

        log(
            "SYSTEM",
            (
                f"RECONCILIAÇÃO {symbol} id={trade_id}: "
                f"falha ao consultar OCO ({error}) — estado real "
                "desconhecido — INTERVENÇÃO MANUAL NECESSÁRIA"
            ),
            "CRITICAL"
        )


async def _emergency_close(client, trade) -> None:

    symbol   = trade.symbol
    trade_id = trade.id

    try:
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


async def _reconcile_orphan_orders(client, open_trades, symbols) -> None:

    # =========================================================
    # Ordens/OCOs abertas na Binance que não têm nenhum trade OPEN
    # correspondente no banco local -- posição aberta fora do bot,
    # ou banco local apagado/perdido. Não sabemos o histórico dessa
    # posição, então só alertamos: nunca cancelamos ou fechamos nada
    # aqui.
    # =========================================================

    if symbols is None:

        from core.config.settings import settings
        symbols = settings.SYMBOLS

    known_order_list_ids = {
        int(trade.order_list_id)
        for trade in open_trades
        if trade.order_list_id
    }

    for symbol in symbols:

        try:
            orders = await client.get_open_orders(symbol=symbol)

        except Exception as error:

            log(
                "SYSTEM",
                (
                    f"RECONCILIAÇÃO {symbol}: falha ao consultar ordens "
                    f"abertas na Binance ({error}) — verificação de "
                    "ordens órfãs pulada para este símbolo"
                ),
                "WARNING"
            )
            continue

        seen_order_list_ids = set()

        for order in orders:

            order_list_id = order.get("orderListId", -1)

            # Já reportada (as duas pernas de uma OCO aparecem como
            # entradas separadas em /api/v3/openOrders)
            if order_list_id in seen_order_list_ids:
                continue

            is_orphan = (
                order_list_id == -1
                or order_list_id not in known_order_list_ids
            )

            if not is_orphan:
                continue

            seen_order_list_ids.add(order_list_id)

            log(
                "SYSTEM",
                (
                    f"RECONCILIAÇÃO {symbol}: ordem órfã na Binance sem "
                    f"trade correspondente no banco local "
                    f"(orderId={order.get('orderId')}, "
                    f"orderListId={order_list_id}) — posição real "
                    "possivelmente sem rastreamento — "
                    "INTERVENÇÃO MANUAL NECESSÁRIA"
                ),
                "CRITICAL"
            )
