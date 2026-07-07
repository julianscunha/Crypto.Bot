# -*- coding: utf-8 -*-

"""
The single decision point between PAPER (simulated, current
behavior) and LIVE (real Binance orders) execution.

== Why this exists ==

core/agents/execution_agent.py always called
trades_repository.create_trade() directly -- there was never a
branch point where "actually place a real order" could be inserted
without it being scattered across the agent itself. This module is
that single point: ExecutionAgent calls execution_router.execute(),
and everything about paper vs. live, and everything about what
"success" or "failure" means for each, lives here.

== Live execution sequence, and why each step is ordered this way ==

1. Place a MARKET BUY order for the entry. If this fails, nothing
   has happened -- reject the signal exactly like a validation
   failure. No funds are at risk yet.

2. Compute the REAL average fill price from the order response
   (cummulativeQuoteQty / executedQty), not the price the signal
   asked for -- market orders fill at whatever the order book gives,
   and the stop loss / take profit levels must be placed relative to
   reality, not the request.

3. Place the protective OCO (take profit + stop loss) using the real
   fill price. This is the dangerous step: if the entry succeeded
   but the OCO fails, the account now holds a REAL, UNPROTECTED
   position -- no stop loss, no take profit, fully exposed to
   whatever the market does next. That is the single worst state
   this code can put a real account into, worse than any rejected
   signal or failed entry, because money is already on the table
   with no safety net.

   The response to that specific failure is not "retry" or "log and
   continue" -- it is to immediately place a MARKET SELL for the
   same quantity, closing the position right away and accepting
   whatever slippage that costs. A small, known, immediate loss from
   slippage is a vastly better outcome than an unprotected position
   left to whatever happens until a human notices.

4. Only after BOTH orders succeed does this record anything in the
   local database. The local trades table must never claim a
   position exists with protection that was never actually placed.

== What "success" means for paper vs. live ==

Paper: identical to the existing behavior before this module
existed -- create_trade() simulates the fill with slippage, no
network calls, can't fail except via local validation.

Live: success requires real confirmation from Binance at each step.
A network error during any of these calls is NOT the same as a
clean rejection -- see BinanceTradingClient/BinanceTradingError's
docstrings -- because the order's true state may be unknown. This
router treats any such uncertainty as a reason to halt and escalate
loudly (ERROR-level log, rejected signal with a distinct reason),
never as a reason to guess and proceed.
"""

from core.services.binance_trading_client import (
    BinanceTradingClient,
    BinanceTradingError,
    MainnetNotConfirmedError,
    _fmt_price,
)

from core.services.position_lifecycle_service import (
    PositionLifecycleService
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.config.settings import (
    settings
)

from core.utils.console_logger import (
    log
)


class ExecutionResult:

    def __init__(
        self,
        success: bool,
        reason: str,
        trade=None
    ):

        self.success = success

        self.reason = reason

        self.trade = trade


class ExecutionRouter:

    def __init__(self):

        self.positions = (
            trades_repository
        )

        self.lifecycle = (
            PositionLifecycleService
        )

        self._client = None

    # =====================================================
    # CLIENT (LAZY, RE-CHECKED EVERY TIME)
    # =====================================================
    #
    # Deliberately not cached as a long-lived singleton attribute
    # set once at import time -- settings.MODE/BINANCE_TESTNET/
    # LIVE_TRADING_CONFIRMED could change between calls (e.g. someone
    # edits .env and restarts just the API, or a future in-process
    # settings reload), and re-evaluating which mode applies on every
    # execute() call is the only way to guarantee a stale client
    # never silently routes to the wrong destination.

    def _build_live_client(self):

        return BinanceTradingClient(

            api_key=settings.BINANCE_API_KEY,

            api_secret=settings.BINANCE_SECRET_KEY,

            testnet=settings.BINANCE_TESTNET,

            live_trading_confirmed=(
                settings.LIVE_TRADING_CONFIRMED
            )
        )

    # =====================================================
    # ENTRY POINT
    # =====================================================

    async def execute(
        self,
        payload
    ):

        mode = settings.MODE.strip().lower()

        if mode == "live":

            return await self._execute_live(
                payload
            )

        return self._execute_paper(
            payload
        )

    # =====================================================
    # PAPER EXECUTION
    # =====================================================
    #
    # Unchanged from ExecutionAgent's pre-existing behavior --
    # simulated fill via PositionLifecycleService's slippage model,
    # no network calls, recorded immediately.

    def _execute_paper(
        self,
        payload
    ):

        executed_entry_price = (

            self.lifecycle
            .apply_entry_slippage(

                payload.entry_price
            )
        )

        trade = (

            self.positions
            .create_trade(

                user_id=payload.user_id,

                symbol=payload.symbol,

                action=payload.signal,

                entry_price=executed_entry_price,

                quantity=payload.quantity,

                stop_loss=payload.stop_loss,

                take_profit=payload.take_profit,

                trailing_stop=payload.trailing_stop
            )
        )

        if not trade:

            return ExecutionResult(
                success=False,

                reason="TRADE_CREATION_FAILED"
            )

        return ExecutionResult(
            success=True,

            reason="PAPER_FILLED",

            trade=trade
        )

    # =====================================================
    # LIVE EXECUTION
    # =====================================================

    async def _execute_live(
        self,
        payload
    ):

        try:

            client = self._build_live_client()

        except MainnetNotConfirmedError as error:

            log(
                "EXECUTION",
                (
                    "LIVE EXECUTION BLOCKED "
                    f"{error}"
                ),
                "ERROR"
            )

            return ExecutionResult(
                success=False,

                reason="MAINNET_NOT_CONFIRMED"
            )

        # =================================================
        # STEP 1: MARKET ENTRY
        # =================================================

        try:

            entry_response = (

                await client
                .place_market_order(

                    symbol=payload.symbol,

                    side="BUY",

                    quantity=payload.quantity
                )
            )

        except BinanceTradingError as error:

            log(
                "EXECUTION",
                (
                    "LIVE ENTRY FAILED "
                    f"symbol={payload.symbol} {error}"
                ),
                "ERROR"
            )

            return ExecutionResult(
                success=False,

                reason="LIVE_ENTRY_FAILED"
            )

        executed_quantity = float(
            entry_response.get(
                "executedQty",
                0
            )
        )

        cumulative_quote_qty = float(
            entry_response.get(
                "cummulativeQuoteQty",
                0
            )
        )

        # Captured here, used at STEP 3 below when the trade is
        # finally recorded -- see add_live_order_tracking_columns
        # for why this needs to survive past this function at all:
        # without it, core/agents/position_manager_agent.py has no
        # way to cancel this position's OCO or confirm its real
        # fill state once it's time to exit.
        entry_order_id = (
            entry_response.get(
                "orderId"
            )
        )

        if (
            executed_quantity <= 0
            or cumulative_quote_qty <= 0
        ):

            log(
                "EXECUTION",
                (
                    "LIVE ENTRY DID NOT FILL "
                    f"symbol={payload.symbol} "
                    f"response={entry_response}"
                ),
                "ERROR"
            )

            return ExecutionResult(
                success=False,

                reason="LIVE_ENTRY_NOT_FILLED"
            )

        # =================================================
        # REAL FILL PRICE
        # =================================================
        #
        # Never the price the signal asked for -- a MARKET order
        # fills at whatever the order book actually gives. Every
        # downstream price (stop loss, take profit, the trade record
        # itself) is relative to this real number.

        average_fill_price = (
            cumulative_quote_qty
            /
            executed_quantity
        )

        stop_loss_distance = (
            payload.entry_price
            -
            payload.stop_loss
        )

        take_profit_distance = (
            payload.take_profit
            -
            payload.entry_price
        )

        real_stop_loss = (
            average_fill_price
            -
            stop_loss_distance
        )

        real_take_profit = (
            average_fill_price
            +
            take_profit_distance
        )

        # =================================================
        # STEP 2: PROTECTIVE OCO
        # =================================================

        try:

            oco_response = (

                await client.place_oco_sell_order(

                    symbol=payload.symbol,

                    quantity=executed_quantity,

                    take_profit_price=_fmt_price(
                        payload.symbol, real_take_profit
                    ),

                    stop_loss_price=_fmt_price(
                        payload.symbol, real_stop_loss
                    ),

                    stop_loss_limit_price=_fmt_price(
                        payload.symbol, real_stop_loss * 0.999
                    )
                )
            )

        except BinanceTradingError as error:

            return await self._handle_unprotected_position(

                client=client,

                payload=payload,

                executed_quantity=executed_quantity,

                average_fill_price=average_fill_price,

                error=error
            )

        # =================================================
        # STEP 3: RECORD ONLY AFTER BOTH ORDERS SUCCEEDED
        # =================================================

        trade = (

            self.positions
            .create_trade(

                user_id=payload.user_id,

                symbol=payload.symbol,

                action=payload.signal,

                entry_price=average_fill_price,

                quantity=executed_quantity,

                stop_loss=real_stop_loss,

                take_profit=real_take_profit,

                trailing_stop=payload.trailing_stop,

                entry_order_id=(
                    str(entry_order_id)
                    if entry_order_id is not None
                    else None
                ),

                order_list_id=(
                    str(
                        oco_response.get(
                            "orderListId"
                        )
                    )
                    if oco_response.get(
                        "orderListId"
                    ) is not None
                    else None
                )
            )
        )

        if not trade:

            # the real position and its real OCO protection both
            # exist on the exchange at this point regardless of
            # whether the local record succeeded -- this is logged
            # as critical because the bot's local state and the
            # exchange's real state have now diverged, and a human
            # needs to reconcile them manually
            log(
                "EXECUTION",
                (
                    "LIVE POSITION OPENED BUT LOCAL RECORD FAILED "
                    f"symbol={payload.symbol} "
                    f"entry={average_fill_price} "
                    f"qty={executed_quantity} -- "
                    "a real, protected position exists on the "
                    "exchange with no matching local trade record. "
                    "Reconcile manually."
                ),
                "ERROR"
            )

            return ExecutionResult(
                success=False,

                reason="LIVE_POSITION_OPENED_RECORD_FAILED"
            )

        log(
            "EXECUTION",
            (
                "LIVE FILLED "
                f"symbol={payload.symbol} "
                f"entry={average_fill_price} "
                f"qty={executed_quantity} "
                f"sl={real_stop_loss} "
                f"tp={real_take_profit}"
            ),
            "SUCCESS"
        )

        return ExecutionResult(
            success=True,

            reason="LIVE_FILLED",

            trade=trade
        )

    # =====================================================
    # UNPROTECTED POSITION HANDLING
    # =====================================================
    #
    # Reached only when the entry succeeded but the OCO failed --
    # see this module's docstring for why this is the single worst
    # state the router can leave a real account in, and why the
    # response is an immediate market close rather than a retry.

    async def _handle_unprotected_position(
        self,
        client,
        payload,
        executed_quantity: float,
        average_fill_price: float,
        error: Exception
    ):

        log(
            "EXECUTION",
            (
                "LIVE OCO PLACEMENT FAILED -- POSITION UNPROTECTED "
                f"symbol={payload.symbol} "
                f"qty={executed_quantity} {error} -- "
                "attempting immediate market close"
            ),
            "ERROR"
        )

        try:

            await client.place_market_order(

                symbol=payload.symbol,

                side="SELL",

                quantity=executed_quantity
            )

            log(
                "EXECUTION",
                (
                    "EMERGENCY CLOSE SUCCEEDED "
                    f"symbol={payload.symbol} -- the unprotected "
                    "position was closed immediately, accepting "
                    "slippage rather than leaving it exposed"
                ),
                "WARNING"
            )

            return ExecutionResult(
                success=False,

                reason="LIVE_OCO_FAILED_POSITION_CLOSED"
            )

        except BinanceTradingError as close_error:

            # the worst case this module is designed around: entry
            # succeeded, protection failed, and the emergency close
            # ALSO failed. A real, unprotected position is open on
            # the exchange and this code has no further automated
            # recourse -- this must be loud enough that a human
            # intervenes immediately.
            log(
                "EXECUTION",
                (
                    "EMERGENCY CLOSE FAILED -- "
                    "REAL UNPROTECTED POSITION IS OPEN "
                    f"symbol={payload.symbol} "
                    f"qty={executed_quantity} "
                    f"entry={average_fill_price} "
                    f"close_error={close_error} -- "
                    "MANUAL INTERVENTION REQUIRED IMMEDIATELY"
                ),
                "ERROR"
            )

            return ExecutionResult(
                success=False,

                reason="LIVE_POSITION_UNPROTECTED_MANUAL_ACTION_REQUIRED"
            )


execution_router = (
    ExecutionRouter()
)
