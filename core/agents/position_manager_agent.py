# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketDataMessage
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.services.position_lifecycle_service import (
    PositionLifecycleService
)

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
)

from core.services.atr_service import (
    atr_service
)

from core.services.market_regime_service import (
    market_regime_service
)

from core.services.binance_trading_client import (
    BinanceTradingClient,
    BinanceTradingError,
    MainnetNotConfirmedError
)

from core.config.settings import (
    settings
)

from core.utils.console_logger import (
    log
)


class PositionManagerAgent:

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        self.positions = (
            trades_repository
        )

        self.lifecycle = (
            PositionLifecycleService
        )

        self.config = (
            TRADE_MANAGEMENT_CONFIG
        )

        self.atr_service = (
            atr_service
        )

        self.market_regime = (
            market_regime_service
        )

        self.bus.subscribe(
            self
        )

    # =====================================================
    # MESSAGE
    # =====================================================

    async def on_message(
        self,
        message
    ):

        if not isinstance(
            message,
            MarketDataMessage
        ):

            return

        payload = (
            message.payload
        )

        open_positions = (

            self.positions.get_open_trades(
                user_id=payload.user_id
            )
        )

        for trade in open_positions:

            if trade.symbol != payload.symbol:

                continue

            await self._process_position(

                trade=trade,

                market_price=payload.close
            )

    # =====================================================
    # LIVE CLIENT
    # =====================================================
    #
    # Mirrors ExecutionRouter._build_live_client() exactly --
    # constructed fresh per call rather than cached, same as there,
    # since BinanceTradingClient is cheap to build and settings can
    # change between calls (e.g. mode switched via the Settings
    # panel, which restarts the Runner -- see README_FULL.md's "Why
    # a restart is needed to change modes at all"). Returns None for
    # PAPER, since none of the LIVE-only exit logic below should
    # ever run against a simulated position.

    def _get_live_client(self):

        if settings.MODE.strip().lower() != "live":

            return None

        try:

            return BinanceTradingClient(

                api_key=settings.BINANCE_API_KEY,

                api_secret=settings.BINANCE_SECRET_KEY,

                testnet=settings.BINANCE_TESTNET,

                live_trading_confirmed=(
                    settings.LIVE_TRADING_CONFIRMED
                )
            )

        except MainnetNotConfirmedError as error:

            log(
                "POSITION",
                (
                    "LIVE CLIENT BLOCKED "
                    f"{error}"
                ),
                "ERROR"
            )

            return None

    # =====================================================
    # PROCESS POSITION
    # =====================================================

    async def _process_position(
        self,
        trade,
        market_price: float
    ):

        # =================================================
        # UNREALIZED PNL
        # =================================================

        unrealized_pnl = (

            self.lifecycle
            .calculate_unrealized_pnl(

                entry_price=trade.entry_price,

                current_price=market_price,

                quantity=trade.quantity
            )
        )

        # =================================================
        # UPDATE TRADE
        # =================================================

        managed_trade = (

            self.positions
            .update_trade_price(

                trade_id=trade.id,

                current_price=market_price,

                unrealized_pnl=unrealized_pnl
            )
        )

        if not managed_trade:

            return

        # =================================================
        # BREAKEVEN
        # =================================================

        await self._apply_breakeven(
            managed_trade,
            market_price
        )

        # =================================================
        # DYNAMIC TAKE PROFIT
        # =================================================

        await self._apply_dynamic_take_profit(
            managed_trade,
            market_price
        )

        # =================================================
        # TRAILING STOP
        # =================================================

        trailing_stop_price = (
            self._calculate_trailing_stop_price(
                managed_trade
            )
        )

        pnl = round(

            managed_trade.unrealized_pnl,

            2
        )

        # =================================================
        # STOP LOSS
        # =================================================

        if market_price <= managed_trade.stop_loss:

            await self._close_position(

                managed_trade,

                market_price,

                "STOP_LOSS",

                pnl,

                "ERROR"
            )

            return

        # =================================================
        # TAKE PROFIT
        # =================================================

        if market_price >= managed_trade.take_profit:

            await self._close_position(

                managed_trade,

                market_price,

                "TAKE_PROFIT",

                pnl,

                "SUCCESS"
            )

            return

        # =================================================
        # TRAILING STOP
        # =================================================

        if market_price <= trailing_stop_price:

            await self._close_position(

                managed_trade,

                market_price,

                "TRAILING_STOP",

                pnl,

                "WARNING"
            )

    # =====================================================
    # BREAKEVEN
    # =====================================================
    #
    # Moves stop_loss to entry_price once unrealized profit reaches
    # breakeven_trigger_percent -- eliminating the risk of a position
    # that was winning turning into a loss. Previously this config
    # existed (enable_breakeven, breakeven_trigger_percent) and a
    # breakeven_enabled column existed on every Trade row, but no
    # code anywhere ever read either -- the feature was fully wired
    # up in data/config but never actually implemented.
    #
    # breakeven_enabled is repurposed here as "breakeven has already
    # been applied to this trade" (it was never meaningfully used as
    # "is enabled for this trade" -- ExecutionAgent always passed
    # True regardless of config) so this only fires once per trade,
    # never re-evaluating or moving the stop again after it's set.

    async def _apply_breakeven(
        self,
        trade,
        market_price: float
    ):

        if not self.config[
            "enable_breakeven"
        ]:

            return

        if trade.breakeven_enabled:

            # already applied to this trade -- never re-trigger
            return

        if trade.entry_price <= 0:

            return

        profit_percent = (

            (
                market_price
                -
                trade.entry_price
            )
            /
            trade.entry_price
        ) * 100

        trigger_percent = self.config[
            "breakeven_trigger_percent"
        ]

        if profit_percent < trigger_percent:

            return

        # only ever moves stop_loss UP (toward/to entry) for a long
        # position -- never applied if it would move the stop
        # backward, which would happen if the trailing stop or a
        # prior adjustment already placed it above entry
        if trade.entry_price <= trade.stop_loss:

            return

        # =================================================
        # LIVE: REPLACE THE REAL OCO BEFORE TOUCHING THE DB
        # =================================================
        #
        # Bug fixed: this previously moved stop_loss in the local
        # row only -- for a LIVE trade, the real protective stop
        # only exists inside the OCO already resting on Binance,
        # and a resting order's leg can't be edited in place. The
        # only way to actually move it is cancel the existing OCO
        # and place a new one with the new stop_loss (same
        # take_profit). If either step fails, the position must not
        # be reported as "protected at breakeven" locally while the
        # real exchange-side stop never moved.

        client = (
            self._get_live_client()
        )

        new_order_list_id = None

        if (
            client is not None
            and trade.order_list_id is not None
        ):

            replaced = (

                await self._replace_oco(

                    client=client,

                    trade=trade,

                    new_stop_loss=trade.entry_price,

                    new_take_profit=trade.take_profit,

                    context="BREAKEVEN"
                )
            )

            if replaced is None:

                # cancel or re-place failed -- the real stop never
                # moved (or the position is now unprotected and
                # being handled by _replace_oco's own emergency
                # path). Either way, do not claim breakeven applied.
                return

            new_order_list_id = replaced

        updated_trade = (

            self.positions
            .update_stop_loss(

                trade_id=trade.id,

                new_stop_loss=trade.entry_price,

                mark_breakeven_applied=True,

                new_order_list_id=new_order_list_id
            )
        )

        if not updated_trade:

            return

        trade.stop_loss = (
            updated_trade.stop_loss
        )

        trade.breakeven_enabled = (
            updated_trade.breakeven_enabled
        )

        if new_order_list_id is not None:

            trade.order_list_id = (
                new_order_list_id
            )

        log(
            "POSITION",
            (
                f"BREAKEVEN symbol={trade.symbol} "
                f"stop_loss_moved_to={trade.entry_price}"
            ),
            "SUCCESS"
        )

    # =====================================================
    # DYNAMIC TAKE PROFIT
    # =====================================================
    #
    # enable_dynamic_take_profit existed in config since early in
    # this project but no code anywhere ever read it -- take_profit
    # was always fixed at whatever RiskAgent calculated at entry
    # time, for the entire life of the position.
    #
    # When enabled, this extends take_profit ONCE, and only when
    # BOTH conditions hold:
    #   1. Price has reached dynamic_take_profit_proximity_percent
    #      of the original entry-to-target distance (default 90%) --
    #      extending right after entry, far from the original
    #      target, would just be guessing; extending only once
    #      price has nearly proven the original target right is a
    #      much narrower, more defensible bet.
    #   2. core.services.market_regime_service reports the symbol's
    #      regime as BULLISH (this codebase is long-only -- see
    #      BinanceTradingClient's docstring -- so a continuing
    #      uptrend is the only direction that justifies giving a
    #      winning position more room) -- a SIDEWAYS/BEARISH/
    #      TRENDING-but-not-BULLISH regime does not extend.
    #
    # The extension amount is dynamic_take_profit_atr_multiplier *
    # the CURRENT ATR (same data source PositionManagerAgent's ATR
    # trailing stop already uses), added on top of the existing
    # take_profit -- consistent with how RiskAgent already sizes the
    # original target from ATR at entry.

    async def _apply_dynamic_take_profit(
        self,
        trade,
        market_price: float
    ):

        if not self.config[
            "enable_dynamic_take_profit"
        ]:

            return

        if trade.take_profit_extended:

            # already applied to this trade -- never re-trigger
            return

        entry_to_target_distance = (
            trade.take_profit
            -
            trade.entry_price
        )

        if entry_to_target_distance <= 0:

            # malformed/inverted target -- nothing sane to extend
            return

        distance_covered = (
            market_price
            -
            trade.entry_price
        )

        proximity_percent = (

            (
                distance_covered
                /
                entry_to_target_distance
            )
            * 100
        )

        required_proximity = self.config[
            "dynamic_take_profit_proximity_percent"
        ]

        if proximity_percent < required_proximity:

            return

        regime = (

            self.market_regime
            .detect_regime(
                trade.symbol
            )
        )

        if regime != "BULLISH":

            return

        current_atr = (

            self.atr_service
            .calculate_atr(

                user_id=trade.user_id,

                symbol=trade.symbol
            )
        )

        if current_atr is None:

            return

        extension_multiplier = self.config[
            "dynamic_take_profit_atr_multiplier"
        ]

        new_take_profit = (

            trade.take_profit
            +
            (
                current_atr
                *
                extension_multiplier
            )
        )

        # =================================================
        # LIVE: REPLACE THE REAL OCO BEFORE TOUCHING THE DB
        # =================================================
        #
        # Bug fixed: this previously extended take_profit in the
        # local row only -- for a LIVE trade, the real target lives
        # inside the OCO already resting on Binance, and a resting
        # order's leg can't be edited in place. See
        # _apply_breakeven's identical reasoning above; this mirrors
        # it exactly, moving take_profit only and leaving stop_loss
        # unchanged.

        client = (
            self._get_live_client()
        )

        new_order_list_id = None

        if (
            client is not None
            and trade.order_list_id is not None
        ):

            replaced = (

                await self._replace_oco(

                    client=client,

                    trade=trade,

                    new_stop_loss=trade.stop_loss,

                    new_take_profit=new_take_profit,

                    context="DYNAMIC_TAKE_PROFIT"
                )
            )

            if replaced is None:

                # cancel or re-place failed -- the real target
                # never moved (or the position is now closed via
                # _replace_oco's own emergency path). Either way,
                # do not claim the extension was applied.
                return

            new_order_list_id = replaced

        updated_trade = (

            self.positions
            .update_take_profit(

                trade_id=trade.id,

                new_take_profit=new_take_profit,

                mark_take_profit_extended=True,

                new_order_list_id=new_order_list_id
            )
        )

        if not updated_trade:

            return

        trade.take_profit = (
            updated_trade.take_profit
        )

        trade.take_profit_extended = (
            updated_trade.take_profit_extended
        )

        if new_order_list_id is not None:

            trade.order_list_id = (
                new_order_list_id
            )

        log(
            "POSITION",
            (
                f"DYNAMIC_TAKE_PROFIT symbol={trade.symbol} "
                f"extended_to={trade.take_profit}"
            ),
            "SUCCESS"
        )

    # =====================================================
    # TRAILING STOP
    # =====================================================

    def _calculate_trailing_stop_price(
        self,
        trade
    ):

        if not self.config[
            "enable_trailing_stop"
        ]:

            return float("-inf")

        if trade.highest_price is None:

            return float("-inf")

        trailing_distance = (
            self._resolve_trailing_distance(
                trade
            )
        )

        return (

            trade.highest_price
            -
            trailing_distance
        )

    # =====================================================
    # TRAILING DISTANCE
    # =====================================================
    #
    # enable_atr_trailing existed in config since early in this
    # project but no code anywhere ever read it -- the trailing
    # distance was always trade.trailing_stop, a value computed
    # once from the ATR at entry time (see RiskAgent's
    # atr * atr_trailing_multiplier) and then frozen for the entire
    # life of the position. That doesn't adapt if volatility changes
    # after entry: a trailing distance sized for calm conditions can
    # get hit by ordinary noise once volatility rises, and one sized
    # for volatile conditions stays too loose (giving back more
    # profit than necessary) once the market calms down.
    #
    # When enabled, this recalculates the distance from the CURRENT
    # ATR every candle instead, using the same
    # atr_trailing_multiplier RiskAgent already uses at entry, so the
    # two stay consistent. Falls back to the frozen entry-time
    # distance if the current ATR isn't available yet (e.g. still in
    # warmup for some other reason) -- never blocks the trailing
    # stop from working at all over a transient missing value.

    def _resolve_trailing_distance(
        self,
        trade
    ):

        if not self.config[
            "enable_atr_trailing"
        ]:

            return trade.trailing_stop

        current_atr = (

            self.atr_service
            .calculate_atr(

                user_id=trade.user_id,

                symbol=trade.symbol
            )
        )

        if current_atr is None:

            return trade.trailing_stop

        atr_trailing_multiplier = (
            self.config[
                "atr_trailing_multiplier"
            ]
        )

        return (
            current_atr
            *
            atr_trailing_multiplier
        )

    # =====================================================
    # CLOSE POSITION
    # =====================================================

    async def _close_position(
        self,
        trade,
        exit_price: float,
        reason: str,
        pnl: float,
        log_level: str
    ):

        # =================================================
        # LIVE: TOUCH THE REAL EXCHANGE FIRST
        # =================================================
        #
        # Bug fixed: this previously only ever updated the local
        # trades row, for BOTH paper and live -- meaning a LIVE
        # TRAILING_STOP exit (which has no resting order on Binance
        # at all) never actually closed the real position, while a
        # STOP_LOSS/TAKE_PROFIT exit (which the OCO should cover)
        # was marked closed locally without ever confirming the OCO
        # actually filled on the exchange. See
        # add_live_order_tracking_columns for the columns this
        # relies on, and execution_router.py's existing
        # _handle_unprotected_position for the precedent this
        # mirrors: a real, unprotected position is worse than any
        # other failure this code can produce.

        client = (
            self._get_live_client()
        )

        if (
            client is not None
            and trade.order_list_id is not None
        ):

            closed_for_real = (

                await self._close_live_position(

                    client=client,

                    trade=trade,

                    reason=reason
                )
            )

            if not closed_for_real:

                # the real position is still open (or its true
                # state is unknown) on the exchange -- never mark
                # it CLOSED locally in that case, since that would
                # make the local database lie about reality. The
                # next candle's on_message will simply try again.
                return

        # =================================================
        # LOCAL RECORD
        # =================================================

        self.positions.close_trade(

            trade_id=trade.id,

            exit_price=exit_price,

            pnl=trade.unrealized_pnl,

            reason=reason
        )

        log(
            "POSITION",
            f"{reason} pnl={pnl}",
            log_level
        )

    # =====================================================
    # LIVE EXIT
    # =====================================================
    #
    # Dispatches to the right real-exchange action depending on
    # exit reason, then reports back whether the real position is
    # now actually closed -- _close_position only writes the local
    # CLOSED record when this returns True.

    async def _close_live_position(
        self,
        client,
        trade,
        reason: str
    ) -> bool:

        if reason == "TRAILING_STOP":

            return (

                await self._close_via_trailing_stop(
                    client=client,
                    trade=trade
                )
            )

        # STOP_LOSS / TAKE_PROFIT: the OCO already resting on
        # Binance should cover this -- confirm it actually filled
        # rather than assuming it did just because the local price
        # feed crossed the threshold this candle. The OCO and this
        # agent's local price feed each react to ticks
        # independently; this candle's local close crossing
        # stop_loss/take_profit does not guarantee Binance's own
        # order book already triggered the matching leg.
        return (

            await self._confirm_oco_filled(
                client=client,
                trade=trade
            )
        )

    # =====================================================
    # CONFIRM OCO FILLED (STOP_LOSS / TAKE_PROFIT)
    # =====================================================

    async def _confirm_oco_filled(
        self,
        client,
        trade
    ) -> bool:

        try:

            status = (

                await client.get_order_list_status(

                    symbol=trade.symbol,

                    order_list_id=int(
                        trade.order_list_id
                    )
                )
            )

        except BinanceTradingError as error:

            log(
                "POSITION",
                (
                    "LIVE OCO STATUS CHECK FAILED "
                    f"symbol={trade.symbol} "
                    f"order_list_id={trade.order_list_id} {error} -- "
                    "will retry on next candle"
                ),
                "WARNING"
            )

            return False

        list_order_status = (
            status.get(
                "listOrderStatus"
            )
        )

        if list_order_status == "ALL_DONE":

            return True

        # EXECUTING (still resting) or any other non-terminal value
        # -- the real OCO has not finished yet, so the local price
        # feed crossing the threshold this candle was either early
        # or the order hasn't been matched yet. Never close locally
        # ahead of the exchange's own confirmation.
        return False

    # =====================================================
    # CLOSE VIA TRAILING STOP (NO RESTING ORDER COVERS THIS)
    # =====================================================
    #
    # A trailing stop exit has no corresponding order sitting on
    # Binance -- the OCO only covers the original fixed
    # stop_loss/take_profit. Closing for real here means: cancel
    # that OCO (since a single quantity can't be sold twice), then
    # place a real MARKET SELL for the same quantity. If the OCO
    # cancel fails because it already filled in the meantime (a
    # real race between this agent's price feed and Binance's own
    # matching engine), that's actually a success case -- the
    # position is already closed for real, just not via the
    # trailing stop path.

    async def _close_via_trailing_stop(
        self,
        client,
        trade
    ) -> bool:

        try:

            await client.cancel_order_list(

                symbol=trade.symbol,

                order_list_id=int(
                    trade.order_list_id
                )
            )

        except BinanceTradingError as error:

            already_resolved = (

                await self._oco_already_resolved(
                    client=client,
                    trade=trade
                )
            )

            if already_resolved:

                # the OCO beat the trailing stop to closing this
                # position -- nothing left to sell, the real
                # position is already closed
                log(
                    "POSITION",
                    (
                        "TRAILING_STOP RACE: OCO ALREADY RESOLVED "
                        f"symbol={trade.symbol} "
                        f"order_list_id={trade.order_list_id} -- "
                        "treating as closed, no market sell needed"
                    ),
                    "WARNING"
                )

                return True

            log(
                "POSITION",
                (
                    "LIVE OCO CANCEL FAILED "
                    f"symbol={trade.symbol} "
                    f"order_list_id={trade.order_list_id} {error} -- "
                    "will retry on next candle"
                ),
                "ERROR"
            )

            return False

        # =================================================
        # REAL MARKET SELL
        # =================================================
        #
        # The OCO is canceled -- the position is now genuinely
        # unprotected on the exchange until this sell lands, exactly
        # the same risk window execution_router.py's
        # _handle_unprotected_position already accepts for a failed
        # entry OCO. There is no safer alternative: leaving the
        # position open is strictly worse than a brief gap with no
        # resting order.

        try:

            await client.place_market_order(

                symbol=trade.symbol,

                side="SELL",

                quantity=trade.quantity
            )

            return True

        except BinanceTradingError as error:

            log(
                "POSITION",
                (
                    "LIVE TRAILING STOP MARKET SELL FAILED -- "
                    "POSITION UNPROTECTED "
                    f"symbol={trade.symbol} "
                    f"qty={trade.quantity} {error} -- "
                    "MANUAL INTERVENTION REQUIRED IMMEDIATELY"
                ),
                "ERROR"
            )

            return False

    # =====================================================
    # OCO ALREADY RESOLVED (RACE CHECK)
    # =====================================================

    async def _oco_already_resolved(
        self,
        client,
        trade
    ) -> bool:

        try:

            status = (

                await client.get_order_list_status(

                    symbol=trade.symbol,

                    order_list_id=int(
                        trade.order_list_id
                    )
                )
            )

        except BinanceTradingError:

            return False

        return (
            status.get(
                "listOrderStatus"
            )
            == "ALL_DONE"
        )

    # =====================================================
    # REPLACE OCO (BREAKEVEN / DYNAMIC TAKE PROFIT)
    # =====================================================
    #
    # A resting OCO's legs can't be edited in place -- moving
    # either stop_loss or take_profit means: cancel the existing
    # OCO, then place a brand new one with the desired levels. This
    # is shared by _apply_breakeven (moves stop_loss only) and
    # _apply_dynamic_take_profit (moves take_profit only) -- each
    # passes the OTHER value unchanged so the leg it isn't touching
    # stays exactly where it was.
    #
    # Returns the new order_list_id (as a string, matching how
    # ExecutionRouter already persists it) on success, or None if
    # anything failed. The position is genuinely unprotected on the
    # exchange during the gap between cancel and the new OCO
    # landing -- the same kind of window execution_router.py's
    # _handle_unprotected_position already accepts for the initial
    # entry OCO. If the new OCO placement itself fails, this falls
    # back to the same immediate-market-sell emergency response,
    # since leaving a real position with literally no resting
    # order at all is worse than closing it outright.

    async def _replace_oco(
        self,
        client,
        trade,
        new_stop_loss: float,
        new_take_profit: float,
        context: str
    ):

        try:

            await client.cancel_order_list(

                symbol=trade.symbol,

                order_list_id=int(
                    trade.order_list_id
                )
            )

        except BinanceTradingError as error:

            already_resolved = (

                await self._oco_already_resolved(
                    client=client,
                    trade=trade
                )
            )

            if already_resolved:

                log(
                    "POSITION",
                    (
                        f"{context} SKIPPED: OCO ALREADY RESOLVED "
                        f"symbol={trade.symbol} "
                        f"order_list_id={trade.order_list_id}"
                    ),
                    "WARNING"
                )

                return None

            log(
                "POSITION",
                (
                    f"{context} OCO CANCEL FAILED "
                    f"symbol={trade.symbol} "
                    f"order_list_id={trade.order_list_id} {error} -- "
                    "stop/target unchanged, will retry next candle"
                ),
                "ERROR"
            )

            return None

        # =================================================
        # NEW OCO
        # =================================================

        from core.services.exchange_filters import format_price

        tp_str  = format_price(trade.symbol, new_take_profit)
        sl_str  = format_price(trade.symbol, new_stop_loss)
        sll_str = format_price(trade.symbol, new_stop_loss * 0.999)

        # Garantir relação de preços: TP > SL > SL_LIMIT
        # Se estiverem invertidos após arredondamento, abortar
        tp_f  = float(tp_str)
        sl_f  = float(sl_str)
        sll_f = float(sll_str)

        if not (tp_f > sl_f > sll_f):
            log(
                "POSITION",
                (
                    f"{context} OCO ABORTADA: relação de preços inválida "
                    f"TP={tp_f} SL={sl_f} SLL={sll_f} symbol={trade.symbol}"
                ),
                "WARNING"
            )
            return None

        try:

            oco_response = (

                await client.place_oco_sell_order(

                    symbol=trade.symbol,

                    quantity=trade.quantity,

                    take_profit_price=tp_str,

                    stop_loss_price=sl_str,

                    stop_loss_limit_price=sll_str
                )
            )

        except BinanceTradingError as error:

            log(
                "POSITION",
                (
                    f"{context} REPLACEMENT OCO FAILED -- "
                    "POSITION UNPROTECTED "
                    f"symbol={trade.symbol} {error} -- "
                    "attempting immediate market close"
                ),
                "ERROR"
            )

            try:

                await client.place_market_order(

                    symbol=trade.symbol,

                    side="SELL",

                    quantity=trade.quantity
                )

                log(
                    "POSITION",
                    (
                        f"{context} EMERGENCY CLOSE SUCCEEDED "
                        f"symbol={trade.symbol} -- position closed "
                        "at market after replacement OCO failure"
                    ),
                    "WARNING"
                )

                self.positions.close_trade(

                    trade_id=trade.id,

                    exit_price=trade.current_price,

                    pnl=trade.unrealized_pnl,

                    reason=f"{context}_EMERGENCY_CLOSE"
                )

            except BinanceTradingError as sell_error:

                log(
                    "POSITION",
                    (
                        f"{context} EMERGENCY CLOSE ALSO FAILED -- "
                        f"symbol={trade.symbol} {sell_error} -- "
                        "MANUAL INTERVENTION REQUIRED IMMEDIATELY"
                    ),
                    "ERROR"
                )

            return None

        new_order_list_id = (
            oco_response.get(
                "orderListId"
            )
        )

        if new_order_list_id is None:

            return None

        return str(
            new_order_list_id
        )