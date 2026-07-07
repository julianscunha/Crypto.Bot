# -*- coding: utf-8 -*-

"""
Unit tests for core/services/binance_trading_client.py

The HMAC signature math is verified against the EXACT known-answer
example from Binance's own API documentation
(https://developers.binance.com/docs/binance-spot-api-docs) -- this
is the single most important thing to get right in this module,
since a subtly wrong signature either rejects every real order
(safe but useless) or, worse, could be wrong in a way that doesn't
fail until a specific edge case in production.

This sandbox's network egress blocks api.binance.com and
testnet.binance.vision (confirmed: same restriction already seen on
the live WebSocket feed and the historical data fetcher in earlier
sessions), so every HTTP call here is mocked. Real connectivity can
only be validated in the user's own environment.
"""

import pytest

from unittest.mock import patch

from core.services.binance_trading_client import (
    BinanceTradingClient,
    BinanceTradingError,
    MainnetNotConfirmedError,
    MAINNET_BASE_URL,
    TESTNET_BASE_URL
)


# this is the EXACT example from Binance's own documentation:
# https://developers.binance.com/docs/binance-spot-api-docs/faqs/web_socket_api_general_info
KNOWN_ANSWER_API_KEY = (
    "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
)

KNOWN_ANSWER_API_SECRET = (
    "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
)

KNOWN_ANSWER_PARAMS = {
    "symbol": "LTCBTC",
    "side": "BUY",
    "type": "LIMIT",
    "timeInForce": "GTC",
    "quantity": "1",
    "price": "0.1",
    "recvWindow": "5000",
    "timestamp": "1499827319559"
}

KNOWN_ANSWER_SIGNATURE = (
    "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"
)


class _FakeResponse:

    def __init__(self, data, status=200, headers=None):

        self._data = data

        self.status = status

        self.headers = headers or {}

    async def json(self):

        return self._data

    async def text(self):

        return str(self._data)

    async def __aenter__(self):

        return self

    async def __aexit__(self, *args):

        return False


class _FakeSession:

    def __init__(self, response_data, status=200):

        self.response_data = response_data

        self.status = status

        self.last_request = None

    def request(self, method, url, headers, timeout):

        self.last_request = {
            "method": method,
            "url": url,
            "headers": headers
        }

        return _FakeResponse(
            self.response_data,
            self.status
        )

    async def __aenter__(self):

        return self

    async def __aexit__(self, *args):

        return False


class TestHmacSignature:

    def test_matches_binance_documentation_known_answer(self):

        client = BinanceTradingClient(
            api_key=KNOWN_ANSWER_API_KEY,
            api_secret=KNOWN_ANSWER_API_SECRET,
            testnet=True
        )

        result = client._sign(
            KNOWN_ANSWER_PARAMS
        )

        assert KNOWN_ANSWER_SIGNATURE in result

    def test_percent_encodes_special_characters(self):

        client = BinanceTradingClient(
            api_key="key",
            api_secret="secret",
            testnet=True
        )

        result = client._sign({
            "symbol": "BTCUSDT",
            "newClientOrderId": "my order:test",
            "timestamp": 123
        })

        query_part = result.split(
            "&signature="
        )[0]

        assert ":" not in query_part

        assert "%3A" in query_part

    def test_different_secrets_produce_different_signatures(self):

        client_a = BinanceTradingClient(
            api_key="key",
            api_secret="secret_a",
            testnet=True
        )

        client_b = BinanceTradingClient(
            api_key="key",
            api_secret="secret_b",
            testnet=True
        )

        params = {"symbol": "BTCUSDT", "timestamp": 123}

        assert (
            client_a._sign(params)
            != client_b._sign(params)
        )


class TestMainnetSafetyLock:

    def test_mainnet_without_confirmation_raises(self):

        with pytest.raises(MainnetNotConfirmedError):

            BinanceTradingClient(
                api_key="k",
                api_secret="s",
                testnet=False,
                live_trading_confirmed=False
            )

    def test_mainnet_with_confirmation_succeeds(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=False,
            live_trading_confirmed=True
        )

        assert client.base_url == MAINNET_BASE_URL

    def test_testnet_never_requires_confirmation(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        assert client.base_url == TESTNET_BASE_URL

    def test_testnet_default_confirmation_is_false(self):

        # confirms the parameter's default doesn't accidentally
        # make mainnet easier to reach than intended
        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        assert client.base_url == TESTNET_BASE_URL


class TestReprMasksSecrets:

    def test_repr_never_contains_the_real_secret(self):

        client = BinanceTradingClient(
            api_key="SUPER_SECRET_KEY_12345",
            api_secret="SUPER_SECRET_SECRET_67890",
            testnet=True
        )

        representation = repr(client)

        assert "SUPER_SECRET_SECRET_67890" not in representation

        assert "SUPER_SECRET_KEY_12345" not in representation

    def test_str_never_contains_the_real_secret(self):

        client = BinanceTradingClient(
            api_key="SUPER_SECRET_KEY_12345",
            api_secret="SUPER_SECRET_SECRET_67890",
            testnet=True
        )

        assert "SUPER_SECRET_SECRET_67890" not in str(
            client
        )


class TestRequestMechanics:

    @pytest.mark.asyncio
    async def test_signed_request_includes_api_key_header(self):

        client = BinanceTradingClient(
            api_key="testkey",
            api_secret="testsecret",
            testnet=True
        )

        fake_session = _FakeSession({
            "balances": []
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.get_account_info()

        assert (
            fake_session.last_request["headers"]["X-MBX-APIKEY"]
            == "testkey"
        )

        assert (
            "signature="
            in fake_session.last_request["url"]
        )

    @pytest.mark.asyncio
    async def test_non_200_response_raises_with_binance_code(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession(
            {
                "code": -1022,
                "msg": "Signature for this request is not valid."
            },
            status=400
        )

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            with pytest.raises(BinanceTradingError) as exc_info:

                await client.get_account_info()

        assert exc_info.value.binance_code == -1022

    @pytest.mark.asyncio
    async def test_network_error_raises_with_unknown_state_warning(
        self
    ):

        import aiohttp

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        class _AlwaysFailsSession:

            def request(self, method, url, headers, timeout):

                raise aiohttp.ClientConnectionError(
                    "simulated network failure"
                )

            async def __aenter__(self):

                return self

            async def __aexit__(self, *args):

                return False

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=_AlwaysFailsSession()
        ):

            with pytest.raises(BinanceTradingError) as exc_info:

                await client.get_account_info()

        assert "UNKNOWN" in str(
            exc_info.value
        )


class TestOcoOrderUsesCurrentEndpoint:

    @pytest.mark.asyncio
    async def test_uses_order_list_oco_endpoint_not_deprecated_one(
        self
    ):

        # POST /api/v3/order/oco is deprecated; this must use
        # POST /api/v3/orderList/oco
        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession({
            "orderListId": 1
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.place_oco_sell_order(
                symbol="BTCUSDT",
                quantity=0.001,
                take_profit_price=110000.0,
                stop_loss_price=95000.0,
                stop_loss_limit_price=94900.0
            )

        url = fake_session.last_request["url"]

        assert "/api/v3/orderList/oco" in url

        assert "/api/v3/order/oco" not in url

    @pytest.mark.asyncio
    async def test_oco_is_always_sell_side(self):

        # this codebase is long-only -- every OCO closes a BUY
        # position, so the OCO itself must always be SELL
        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession({
            "orderListId": 1
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.place_oco_sell_order(
                symbol="BTCUSDT",
                quantity=0.001,
                take_profit_price=110000.0,
                stop_loss_price=95000.0,
                stop_loss_limit_price=94900.0
            )

        assert (
            "side=SELL"
            in fake_session.last_request["url"]
        )

    @pytest.mark.asyncio
    async def test_oco_above_is_take_profit_below_is_stop_loss(
        self
    ):

        # per Binance's SELL-side OCO price rule:
        # (TAKE_PROFIT) price > last price > (STOP_LOSS) stopPrice
        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession({
            "orderListId": 1
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.place_oco_sell_order(
                symbol="BTCUSDT",
                quantity=0.001,
                take_profit_price=110000.0,
                stop_loss_price=95000.0,
                stop_loss_limit_price=94900.0
            )

        url = fake_session.last_request["url"]

        assert "aboveType=TAKE_PROFIT_LIMIT" in url

        assert "belowType=STOP_LOSS_LIMIT" in url


class TestClientOrderIdGeneration:

    def test_auto_generated_id_is_within_binance_36_char_limit(
        self
    ):

        # Binance Spot's documented limit for newClientOrderId/
        # listClientOrderId is 36 characters
        generated = (
            BinanceTradingClient._generate_client_order_id()
        )

        assert len(generated) <= 36

    def test_auto_generated_ids_are_unique(self):

        first = (
            BinanceTradingClient._generate_client_order_id()
        )

        second = (
            BinanceTradingClient._generate_client_order_id()
        )

        assert first != second

    @pytest.mark.asyncio
    async def test_market_order_auto_generates_client_order_id_if_not_given(
        self
    ):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession({
            "orderId": 1,
            "status": "FILLED"
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.place_market_order(
                symbol="BTCUSDT",
                side="BUY",
                quantity=1.0
            )

        assert (
            "newClientOrderId="
            in fake_session.last_request["url"]
        )

    @pytest.mark.asyncio
    async def test_market_order_uses_provided_client_order_id(
        self
    ):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession({
            "orderId": 1,
            "status": "FILLED"
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.place_market_order(
                symbol="BTCUSDT",
                side="BUY",
                quantity=1.0,
                client_order_id="my-custom-id-123"
            )

        assert (
            "my-custom-id-123"
            in fake_session.last_request["url"]
        )

    @pytest.mark.asyncio
    async def test_oco_uses_list_client_order_id(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession({
            "orderListId": 1
        })

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            await client.place_oco_sell_order(
                symbol="BTCUSDT",
                quantity=0.001,
                take_profit_price=110000.0,
                stop_loss_price=95000.0,
                stop_loss_limit_price=94900.0
            )

        assert (
            "listClientOrderId="
            in fake_session.last_request["url"]
        )


class TestRateLimitRetry:

    """
    Bug fixed: binance_trading_client.py had no rate-limit handling
    at all -- unlike data/ingestion/binance_history.py (which
    retries 429s with backoff), a 429/418 hitting the order-placement
    client previously failed outright with no retry, exactly when
    fast, reliable execution matters most (e.g. during a volatile
    move that's also triggering more frequent signal evaluation).

    Deliberately NOT extended to network errors/timeouts -- per
    Binance's own documentation, a network failure during a
    TRADE-weight request leaves the order's true state genuinely
    unknown ("the execution status is UNKNOWN and could have been a
    success"), and blindly retrying in that state risks placing the
    same order twice. A 429/418 is different: the request was
    rejected before reaching the matching engine, so retrying after
    the documented Retry-After wait is safe.
    """

    @pytest.mark.asyncio
    async def test_retries_after_429_and_succeeds(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession(
            {"orderId": 1, "status": "FILLED"}
        )

        call_count = {"n": 0}

        original_request = fake_session.request

        def counting_request(method, url, headers, timeout):

            call_count["n"] += 1

            if call_count["n"] == 1:

                return _FakeResponse(
                    {
                        "code": -1015,
                        "msg": "Too many orders"
                    },
                    status=429,
                    headers={"Retry-After": "0"}
                )

            return original_request(
                method, url, headers, timeout
            )

        fake_session.request = counting_request

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            result = await client.get_account_info()

        assert result == {
            "orderId": 1,
            "status": "FILLED"
        }

        assert call_count["n"] == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries_and_raises_on_persistent_429(
        self
    ):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        class _AlwaysRateLimitedSession:

            def __init__(self):

                self.calls = 0

            def request(self, method, url, headers, timeout):

                self.calls += 1

                return _FakeResponse(
                    {
                        "code": -1015,
                        "msg": "persistent rate limit"
                    },
                    status=429,
                    headers={"Retry-After": "0"}
                )

            async def __aenter__(self):

                return self

            async def __aexit__(self, *args):

                return False

        fake_session = _AlwaysRateLimitedSession()

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            with pytest.raises(BinanceTradingError):

                await client.get_account_info()

        assert fake_session.calls == 3

    @pytest.mark.asyncio
    async def test_418_ban_is_also_retried(self):

        # 418 (IP ban after repeated 429s) carries the same
        # Retry-After semantics as 429 per Binance's documentation
        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        fake_session = _FakeSession(
            {"balances": []}
        )

        call_count = {"n": 0}

        original_request = fake_session.request

        def counting_request(method, url, headers, timeout):

            call_count["n"] += 1

            if call_count["n"] == 1:

                return _FakeResponse(
                    {
                        "code": -1003,
                        "msg": "IP banned"
                    },
                    status=418,
                    headers={"Retry-After": "0"}
                )

            return original_request(
                method, url, headers, timeout
            )

        fake_session.request = counting_request

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            result = await client.get_account_info()

        assert result == {"balances": []}

    @pytest.mark.asyncio
    async def test_network_error_is_never_auto_retried(self):

        # this is the critical safety boundary: a network error
        # leaves order state unknown, so retrying automatically
        # risks duplicate orders -- it must raise immediately, not
        # go through the rate-limit retry loop
        import aiohttp

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        class _AlwaysFailsSession:

            def __init__(self):

                self.calls = 0

            def request(self, method, url, headers, timeout):

                self.calls += 1

                raise aiohttp.ClientConnectionError(
                    "simulated network failure"
                )

            async def __aenter__(self):

                return self

            async def __aexit__(self, *args):

                return False

        fake_session = _AlwaysFailsSession()

        with patch(
            "core.services.binance_trading_client."
            "aiohttp.ClientSession",
            return_value=fake_session
        ):

            with pytest.raises(BinanceTradingError):

                await client.get_account_info()

        assert fake_session.calls == 1

    def test_parses_retry_after_header(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        class _FakeHeaderResponse:

            headers = {"Retry-After": "7"}

        result = client._parse_retry_after(
            _FakeHeaderResponse(),
            default=2.0
        )

        assert result == 7.0

    def test_falls_back_to_default_when_header_missing(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        class _FakeHeaderResponse:

            headers = {}

        result = client._parse_retry_after(
            _FakeHeaderResponse(),
            default=4.0
        )

        assert result == 4.0

    def test_falls_back_to_default_when_header_is_malformed(self):

        client = BinanceTradingClient(
            api_key="k",
            api_secret="s",
            testnet=True
        )

        class _FakeHeaderResponse:

            headers = {"Retry-After": "not-a-number"}

        result = client._parse_retry_after(
            _FakeHeaderResponse(),
            default=3.0
        )

        assert result == 3.0
