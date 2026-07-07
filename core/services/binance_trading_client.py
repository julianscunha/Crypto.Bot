# -*- coding: utf-8 -*-

"""
Authenticated REST client for Binance Spot trading (account info,
order placement, order cancellation, order status).

This is intentionally separate from data/ingestion/binance_ws.py
(market data, public, unauthenticated) and
data/ingestion/binance_history.py (historical klines, also public)
-- this module is the ONLY place in the codebase that sends signed,
authenticated requests capable of placing or canceling real orders.

== MAINNET SAFETY ==

Reaching mainnet (real funds) requires BOTH of:
  1. settings.BINANCE_TESTNET == False
  2. settings.LIVE_TRADING_CONFIRMED == True

LIVE_TRADING_CONFIRMED is a separate env var from MODE/BINANCE_TESTNET
on purpose. A person could set MODE=live and BINANCE_TESTNET=false in
one edit while believing they were still configuring testnet --
that single edit must not be enough to enable real-money order
placement. LIVE_TRADING_CONFIRMED has to be deliberately set to true
as its own, explicit step. See core/config/settings.py for the
default (false) and core/services/execution_router.py for where this
gate is actually enforced before any order reaches this client.

This client itself does not decide paper vs. live -- that decision
belongs to execution_router.py. This module will happily place a
real order on mainnet if asked to and the safety checks above pass;
it is not itself a safety mechanism, it is the thing the safety
mechanism guards.

== SIGNING ==

As of the 2026-01-15 Binance API change, signed request payloads
must be percent-encoded before computing the HMAC-SHA256 signature,
or the request is rejected with -1022 INVALID_SIGNATURE. This client
builds the query string with urllib.parse.urlencode (which
percent-encodes by default) and signs that exact string -- the same
string is then sent as the request body, so the signature always
matches what was actually transmitted.
"""

import asyncio

import hashlib

import hmac

import time

import urllib.parse

import uuid

import aiohttp


def _fmt_qty(symbol: str, qty: float) -> str:
    from core.services.exchange_filters import format_quantity
    return format_quantity(symbol, qty)


def _fmt_price(symbol: str, price: float) -> str:
    from core.services.exchange_filters import format_price
    return format_price(symbol, price)


MAINNET_BASE_URL = (
    "https://api.binance.com"
)

TESTNET_BASE_URL = (
    "https://testnet.binance.vision"
)

RECV_WINDOW_MS = 5000

REQUEST_TIMEOUT_SECONDS = 10

# =====================================================
# RATE LIMITING (429 / 418)
# =====================================================
#
# Per Binance's own documentation: "When a 429 is received, it's
# your obligation as an API user/trader to back off and not spam
# the API" -- repeated 429s escalate to a 418 IP ban (2 minutes to
# 3 days, scaling with repeat offenses). Both responses include a
# Retry-After header specifying exactly how long to wait.
#
# Deliberately NOT applied to network errors/timeouts (see
# _request's except clause below) -- those leave the order's true
# state genuinely unknown (Binance's own docs: "It is important to
# NOT treat this as a failure operation; the execution status is
# UNKNOWN and could have been a success"), and retrying an order
# placement blindly in that state risks placing it twice. A 429/418
# is different: the request was definitely rejected before
# reaching the matching engine, so retrying after the required wait
# is safe.

MAX_RATE_LIMIT_RETRIES = 3

DEFAULT_RATE_LIMIT_RETRY_SECONDS = 2


class BinanceTradingError(
    Exception
):

    """
    Raised for any non-2xx response from a signed/trading endpoint,
    or for a network failure while attempting one. Callers
    (execution_router.py) must treat this as "the order's true state
    is unknown" rather than "the order failed" -- see the module
    docstring in execution_router.py for the reconciliation
    consequences of that distinction.
    """

    def __init__(
        self,
        message: str,
        binance_code: int | None = None
    ):

        super().__init__(
            message
        )

        self.binance_code = (
            binance_code
        )


class MainnetNotConfirmedError(
    Exception
):

    """
    Raised when something attempts to construct a mainnet-targeting
    client without LIVE_TRADING_CONFIRMED having been explicitly set.
    This is a programming-time safety net, not the only gate --
    execution_router.py checks the same condition before ever
    constructing this client at all, so this should never actually
    trigger in normal operation. It exists so that a future bug in
    execution_router.py's check fails loudly here instead of silently
    placing a real order.
    """

    pass


class BinanceTradingClient:

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool,
        live_trading_confirmed: bool = False
    ):

        if not testnet and not live_trading_confirmed:

            raise MainnetNotConfirmedError(
                "Refusing to construct a mainnet-targeting "
                "BinanceTradingClient without "
                "live_trading_confirmed=True. This is a real-money "
                "safety check -- see LIVE_TRADING_CONFIRMED in "
                "core/config/settings.py."
            )

        self.api_key = (
            api_key
        )

        self.api_secret = (
            api_secret
        )

        self.testnet = (
            testnet
        )

        self.base_url = (
            TESTNET_BASE_URL
            if testnet
            else MAINNET_BASE_URL
        )

    # =====================================================
    # REPR (SECRET-SAFE)
    # =====================================================
    #
    # Defense in depth: api_key/api_secret are real attributes (read
    # by _sign()/_request()), so vars(client) or a debugger
    # inspecting the object would otherwise show them in plain text.
    # Any logger/exception handler that captures locals() or calls
    # repr() on this object (some frameworks do, on uncaught
    # exceptions) must never be the thing that leaks a real
    # credential into a log file.

    def __repr__(self):

        return (
            f"BinanceTradingClient("
            f"base_url={self.base_url!r}, "
            f"testnet={self.testnet}, "
            f"api_key=***masked***)"
        )

    # =====================================================
    # SIGNING
    # =====================================================

    def _sign(
        self,
        params: dict
    ) -> str:

        query_string = (
            urllib.parse.urlencode(
                params
            )
        )

        signature = hmac.new(

            self.api_secret.encode(
                "utf-8"
            ),

            query_string.encode(
                "utf-8"
            ),

            hashlib.sha256

        ).hexdigest()

        return (
            f"{query_string}&signature={signature}"
        )

    def _build_signed_params(
        self,
        params: dict
    ) -> dict:

        signed_params = dict(
            params
        )

        signed_params["timestamp"] = int(
            time.time() * 1000
        )

        signed_params["recvWindow"] = (
            RECV_WINDOW_MS
        )

        return signed_params

    # =====================================================
    # HTTP
    # =====================================================

    async def _request(
        self,
        method: str,
        path: str,
        params: dict,
        signed: bool
    ):

        headers = {
            "X-MBX-APIKEY": self.api_key
        }

        if signed:

            full_params = (
                self._build_signed_params(
                    params
                )
            )

            signed_query_string = (
                self._sign(
                    full_params
                )
            )

            url = (
                f"{self.base_url}{path}?{signed_query_string}"
            )

        else:

            query_string = (
                urllib.parse.urlencode(
                    params
                )
            )

            url = (
                f"{self.base_url}{path}"
                + (
                    f"?{query_string}"
                    if query_string
                    else ""
                )
            )

        last_rate_limit_error = None

        for attempt in range(
            1,
            MAX_RATE_LIMIT_RETRIES + 1
        ):

            try:

                async with aiohttp.ClientSession() as session:

                    async with session.request(

                        method,

                        url,

                        headers=headers,

                        timeout=aiohttp.ClientTimeout(
                            total=REQUEST_TIMEOUT_SECONDS
                        )

                    ) as response:

                        if response.status in (
                            429,
                            418
                        ):

                            retry_after = (
                                self._parse_retry_after(
                                    response,

                                    default=(
                                        DEFAULT_RATE_LIMIT_RETRY_SECONDS
                                        * attempt
                                    )
                                )
                            )

                            body_preview = await response.text()

                            last_rate_limit_error = (
                                BinanceTradingError(
                                    (
                                        f"Binance rate limit "
                                        f"(status={response.status}) "
                                        f"calling {method} {path}: "
                                        f"{body_preview[:200]}"
                                    )
                                )
                            )

                            if attempt == MAX_RATE_LIMIT_RETRIES:

                                break

                            await asyncio.sleep(
                                retry_after
                            )

                            continue

                        body = await response.json()

                        if response.status != 200:

                            binance_code = (
                                body.get("code")
                                if isinstance(body, dict)
                                else None
                            )

                            binance_msg = (
                                body.get("msg")
                                if isinstance(body, dict)
                                else str(body)
                            )

                            raise BinanceTradingError(
                                (
                                    f"Binance API error "
                                    f"(status={response.status}, "
                                    f"code={binance_code}): "
                                    f"{binance_msg}"
                                ),
                                binance_code=binance_code
                            )

                        return body

            except BinanceTradingError:

                raise

            except (
                aiohttp.ClientError,
                TimeoutError
            ) as error:

                # network-level failure during a TRADE-weight request:
                # the order's true state on the exchange is genuinely
                # unknown here (it may have been received and processed
                # before the network failure occurred) -- this is NOT
                # the same as a confirmed rejection, and callers must
                # not treat it as "no order was placed". Deliberately
                # not retried automatically for that reason -- see this
                # method's rate-limit retry above for the case where
                # retrying IS safe (a 429/418 means the request was
                # rejected before reaching the matching engine at all).
                raise BinanceTradingError(
                    (
                        f"Network error calling {method} {path}: "
                        f"{error}. Order state on the exchange is "
                        "UNKNOWN -- do not assume it was not placed."
                    )
                ) from error

        raise last_rate_limit_error

    @staticmethod
    def _parse_retry_after(
        response,
        default: float
    ) -> float:

        raw_value = response.headers.get(
            "Retry-After"
        )

        if raw_value is None:

            return default

        try:

            return float(
                raw_value
            )

        except ValueError:

            return default

    # =====================================================
    # ACCOUNT
    # =====================================================

    async def get_account_info(
        self
    ):

        return await self._request(
            "GET",
            "/api/v3/account",
            {},
            signed=True
        )

    async def get_symbol_filters(
        self,
        symbol: str
    ):

        """
        Retorna stepSize (LOT_SIZE) e tickSize (PRICE_FILTER)
        para o símbolo. Usado para formatar quantity e preços
        corretamente antes de enviar ordens.
        """

        result = await self._request(
            "GET",
            "/api/v3/exchangeInfo",
            {"symbol": symbol},
            signed=False
        )

        filters = {}

        for sym in result.get("symbols", []):
            if sym.get("symbol") != symbol:
                continue
            for f in sym.get("filters", []):
                if f["filterType"] == "LOT_SIZE":
                    # número de casas decimais do stepSize
                    filters["qty_precision"] = (
                        len(f["stepSize"].rstrip("0").split(".")[-1])
                        if "." in f["stepSize"]
                        else 0
                    )
                    filters["min_qty"] = float(f["minQty"])
                if f["filterType"] == "PRICE_FILTER":
                    filters["price_precision"] = (
                        len(f["tickSize"].rstrip("0").split(".")[-1])
                        if "." in f["tickSize"]
                        else 0
                    )
                    filters["tick_size"] = float(f["tickSize"])
                if f["filterType"] in ("MIN_NOTIONAL", "NOTIONAL"):
                    filters["min_notional"] = float(
                        f.get("minNotional", f.get("notional", 0))
                    )

        return filters

    async def get_symbol_price(
        self,
        symbol: str
    ):

        return await self._request(
            "GET",
            "/api/v3/ticker/price",
            {"symbol": symbol},
            signed=False
        )

    async def get_open_orders(
        self,
        symbol: str | None = None
    ):

        params = (
            {"symbol": symbol}
            if symbol
            else {}
        )

        return await self._request(
            "GET",
            "/api/v3/openOrders",
            params,
            signed=True
        )

    # =====================================================
    # MARKET ORDER (ENTRY)
    # =====================================================

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str | None = None
    ):

        """
        side: "BUY" or "SELL". This codebase only ever opens
        positions with side="BUY" (see ExecutionAgent's
        _validate_execution, which already rejects any signal that
        isn't "BUY") -- SELL support here exists for completeness
        and for closing a position manually if an OCO needs to be
        canceled first, not for opening short positions.

        client_order_id: passed as Binance's newClientOrderId.
        Auto-generated if not provided. Binance only accepts a
        repeated clientOrderId once the prior order under that same
        ID has been filled or expired -- a caller that retries a
        failed/ambiguous request (e.g. after a network error, where
        the order's true state is unknown) with the SAME
        client_order_id is protected from accidentally placing the
        same order twice.
        """

        return await self._request(

            "POST",

            "/api/v3/order",

            {
                "symbol": symbol,

                "side": side,

                "type": "MARKET",

                # Formata usando stepSize real do símbolo (carregado no startup).
                # Evita LOT_SIZE rejection por casas decimais incompatíveis.
                "quantity": _fmt_qty(symbol, quantity),

                "newClientOrderId": (
                    client_order_id
                    or self._generate_client_order_id()
                ),

                "newOrderRespType": "FULL"
            },

            signed=True
        )

    @staticmethod
    def _generate_client_order_id() -> str:

        # Binance Spot's documented limit is 36 characters total --
        # "cb-" (3) + 32 hex chars (a full uuid4 with no dashes) = 35,
        # safely under that limit
        return (
            "cb-"
            +
            uuid.uuid4().hex
        )

    # =====================================================
    # OCO (STOP LOSS + TAKE PROFIT, ATTACHED ON ENTRY)
    # =====================================================

    async def place_oco_sell_order(
        self,
        symbol: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        stop_loss_limit_price: float,
        list_client_order_id: str | None = None
    ):

        """
        Places the protective OCO pair for a position that was
        entered with a BUY -- this OCO is on the SELL side, exactly
        mirroring core/agents/risk_agent.py's existing stop_loss/
        take_profit calculation for a long-only BUY position.

        Uses POST /api/v3/orderList/oco (the current, non-deprecated
        endpoint as of this writing -- POST /api/v3/order/oco is
        deprecated and intentionally not used here).

        For a SELL-side OCO, Binance requires:
            (TAKE_PROFIT/LIMIT_MAKER) price > last price > (STOP_LOSS) stopPrice
        i.e. "above" = take profit, "below" = stop loss.

        stop_loss_limit_price should be set slightly below
        stop_loss_price (the trigger) so the resulting STOP_LOSS_LIMIT
        sell order can actually fill during a fast drop instead of
        sitting unfilled above the falling market price.

        list_client_order_id: passed as Binance's listClientOrderId
        (the OCO-level equivalent of newClientOrderId). Auto-generated
        if not provided -- same retry-safety reasoning as
        place_market_order's client_order_id.
        """

        return await self._request(

            "POST",

            "/api/v3/orderList/oco",

            {
                "symbol": symbol,

                "side": "SELL",

                "quantity": _fmt_qty(symbol, quantity),

                "listClientOrderId": (
                    list_client_order_id
                    or self._generate_client_order_id()
                ),

                "aboveType": "TAKE_PROFIT_LIMIT",

                "abovePrice": _fmt_price(symbol, take_profit_price),

                "aboveStopPrice": _fmt_price(symbol, take_profit_price),

                "aboveTimeInForce": "GTC",

                "belowType": "STOP_LOSS_LIMIT",

                "belowPrice": _fmt_price(symbol, stop_loss_limit_price),

                "belowStopPrice": _fmt_price(symbol, stop_loss_price),

                "belowTimeInForce": "GTC",

                "newOrderRespType": "FULL"
            },

            signed=True
        )

    # =====================================================
    # CANCEL
    # =====================================================

    async def cancel_order_list(
        self,
        symbol: str,
        order_list_id: int
    ):

        return await self._request(

            "DELETE",

            "/api/v3/orderList",

            {
                "symbol": symbol,

                "orderListId": order_list_id
            },

            signed=True
        )

    async def cancel_order(
        self,
        symbol: str,
        order_id: int
    ):

        return await self._request(

            "DELETE",

            "/api/v3/order",

            {
                "symbol": symbol,

                "orderId": order_id
            },

            signed=True
        )

    # =====================================================
    # ORDER STATUS
    # =====================================================

    async def get_order_list_status(
        self,
        symbol: str,
        order_list_id: int
    ):

        return await self._request(

            "GET",

            "/api/v3/orderList",

            {
                "symbol": symbol,

                "orderListId": order_list_id
            },

            signed=True
        )

    async def get_order(
        self,
        symbol: str,
        order_id: int
    ):

        return await self._request(

            "GET",

            "/api/v3/order",

            {
                "symbol": symbol,

                "orderId": order_id
            },

            signed=True
        )
