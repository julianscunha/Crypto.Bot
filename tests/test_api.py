# -*- coding: utf-8 -*-

"""
Tests for the FastAPI app in apps/api/main.py
"""

import pytest

import json

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.api.main import app, DEFAULT_USER_ID
import apps.api.main as api_main

from data.storage.repositories.trades_repository import (
    trades_repository
)

from data.storage.repositories.portfolio_repository import (
    portfolio_repository
)

from data.storage.repositories.runtime_state_repository import (
    runtime_state_repository
)

from core.state.market_state import (
    MarketState
)


@pytest.fixture
def client():

    return TestClient(app)


class TestRootAndHealth:

    def test_root_returns_status_running(self, client):

        response = client.get("/")

        assert response.status_code == 200

        body = response.json()

        assert body["status"] == "running"

        assert body["name"] == "Crypto.Bot"

    def test_health_returns_ok(self, client):

        response = client.get("/health")

        assert response.status_code == 200

        assert response.json()["status"] == "ok"


class TestRuntimeEndpoint:

    @pytest.fixture(autouse=True)
    def _reset_runtime_state(self):

        runtime_state_repository.reset()

        yield

    def test_runtime_returns_200(self, client):

        response = client.get("/runtime")

        assert response.status_code == 200

        body = response.json()

        assert "websocket_connected" in body

        assert "uptime_seconds" in body

    def test_falls_back_to_local_memory_when_runner_never_flushed(
        self,
        client
    ):

        # no Runner process has ever called runtime_state_repository
        # .upsert() -- API standalone, or Full Stack just started.
        # Must not crash, must return sane zeroed defaults.

        response = client.get("/runtime")

        assert response.status_code == 200

        body = response.json()

        assert body["websocket_connected"] is False

    def test_reflects_state_flushed_by_a_separate_process(
        self,
        client
    ):

        # regression: this is the core cross-process bug.
        # market_state in this test process represents what would
        # be the Runner's in-memory state; persisting it via the
        # repository and then hitting /runtime simulates the API
        # process (which never touches this particular MarketState
        # instance) correctly reflecting it anyway.

        runner_side_state = MarketState()

        runner_side_state.set_websocket_connected(True)

        runner_side_state.register_kline("BTCUSDT")

        runner_side_state.register_kline("ETHUSDT")

        runner_side_state.register_analysis_request()

        runner_side_state.register_generated_signal()

        runner_side_state.register_approved_signal()

        runner_side_state.register_order_execution()

        runtime_state_repository.upsert(
            runner_side_state.snapshot()
        )

        response = client.get("/runtime")

        body = response.json()

        assert body["websocket_connected"] is True

        assert sorted(body["active_symbols"]) == [
            "BTCUSDT",
            "ETHUSDT"
        ]

        assert body["total_analysis_requests"] == 1

        assert body["total_generated_signals"] == 1

        assert body["total_approved_signals"] == 1

        assert body["total_executed_orders"] == 1

    def test_dashboard_endpoint_also_reflects_flushed_state(
        self,
        client
    ):

        runner_side_state = MarketState()

        runner_side_state.set_websocket_connected(True)

        runner_side_state.register_kline("BTCUSDT")

        runtime_state_repository.upsert(
            runner_side_state.snapshot()
        )

        response = client.get("/dashboard")

        body = response.json()

        assert body["runtime"]["websocket_connected"] is True

        assert "BTCUSDT" in body["runtime"]["active_symbols"]


class TestPortfolioEndpoint:

    def test_portfolio_with_no_snapshots_returns_empty_defaults(
        self,
        client
    ):

        response = client.get("/portfolio")

        assert response.status_code == 200

        body = response.json()

        assert body["balance"] == 0.0

        assert body["equity"] == 0.0

    def test_portfolio_returns_latest_snapshot(self, client):

        portfolio_repository.create_snapshot(
            user_id=DEFAULT_USER_ID,
            balance=150.0,
            equity=160.0,
            realized_pnl=50.0,
            unrealized_pnl=10.0,
            total_pnl=60.0,
            open_positions=1,
            closed_positions=2,
            exposure=20.0,
            drawdown=5.0
        )

        response = client.get("/portfolio")

        assert response.status_code == 200

        body = response.json()

        assert body["balance"] == 150.0

        assert body["equity"] == 160.0


class TestMetricsEndpoint:

    def test_metrics_with_no_trades_returns_zeroed_metrics(
        self,
        client
    ):

        response = client.get("/metrics")

        assert response.status_code == 200

        body = response.json()

        assert body["total_trades"] == 0

    def test_metrics_response_matches_schema(self, client):

        response = client.get("/metrics")

        assert response.status_code == 200

        body = response.json()

        for key in (
            "total_trades",
            "winrate",
            "pnl"
        ):

            assert key in body


class TestAdvancedMetricsEndpoint:

    def test_returns_200_with_no_trades(self, client):

        response = client.get("/metrics/advanced")

        assert response.status_code == 200

        body = response.json()

        assert body["sample_size"] == 0

        assert body["sharpe_ratio"] == 0.0

    def test_response_matches_schema(self, client):

        response = client.get("/metrics/advanced")

        body = response.json()

        for key in (
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "profit_factor",
            "risk_reward",
            "recovery_factor",
            "max_win_streak",
            "max_loss_streak",
            "current_win_streak",
            "current_loss_streak",
            "sample_size"
        ):

            assert key in body

    def test_reflects_real_closed_trades(self, client):

        trade = trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.close_trade(
            trade_id=trade.id,
            exit_price=110.0,
            pnl=10.0,
            reason="TAKE_PROFIT"
        )

        response = client.get("/metrics/advanced")

        body = response.json()

        assert body["sample_size"] == 1

        assert body["max_win_streak"] == 1

        assert body["current_win_streak"] == 1


class TestRiskStatusEndpoint:

    def test_returns_200_with_no_activity(self, client):

        response = client.get("/risk-status")

        assert response.status_code == 200

        body = response.json()

        assert body["trading_halted"] is False

        assert body["halt_reason"] is None

    def test_response_matches_schema(self, client):

        response = client.get("/risk-status")

        body = response.json()

        for key in (
            "trading_halted",
            "halt_reason",
            "daily_pnl",
            "daily_loss_percent",
            "max_daily_loss_percent",
            "daily_trade_count",
            "max_daily_trades",
            "day_started_at"
        ):

            assert key in body

    def test_reflects_a_real_daily_loss_breach(self, client):

        from core.config.trading_config import TRADING_CONFIG

        account_balance = TRADING_CONFIG["account_balance"]

        max_loss_percent = (
            TRADING_CONFIG["max_daily_loss_percent"]
        )

        loss_amount = (
            account_balance
            *
            (max_loss_percent + 5)
            / 100
        )

        trade = trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        trades_repository.close_trade(
            trade_id=trade.id,
            exit_price=100.0 - loss_amount,
            pnl=-loss_amount,
            reason="STOP_LOSS"
        )

        response = client.get("/risk-status")

        body = response.json()

        assert body["trading_halted"] is True

        assert body["halt_reason"] == "DAILY_LOSS_LIMIT_REACHED"


class TestOpenTradesEndpoint:

    def test_open_trades_returns_list(self, client):

        response = client.get("/trades/open")

        assert response.status_code == 200

        assert isinstance(response.json(), list)

    def test_open_trades_reflects_created_trade(self, client):

        trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        response = client.get("/trades/open")

        body = response.json()

        assert len(body) == 1

        assert body[0]["symbol"] == "BTCUSDT"

        assert body[0]["status"] == "OPEN"


class TestClosedTradesEndpoint:

    def test_closed_trades_returns_list(self, client):

        response = client.get("/trades/closed")

        assert response.status_code == 200

        assert isinstance(response.json(), list)

    def test_closed_trades_reflects_closed_trade(self, client):

        trade = trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="ETHUSDT",
            action="BUY",
            entry_price=2000.0,
            quantity=1.0,
            stop_loss=1900.0,
            take_profit=2200.0,
            trailing_stop=10.0
        )

        trades_repository.close_trade(
            trade_id=trade.id,
            exit_price=2200.0,
            pnl=200.0,
            reason="TAKE_PROFIT"
        )

        response = client.get("/trades/closed")

        body = response.json()

        assert len(body) == 1

        assert body[0]["exit_reason"] == "TAKE_PROFIT"


class TestDashboardEndpoint:

    def test_dashboard_returns_combined_payload(self, client):

        response = client.get("/dashboard")

        assert response.status_code == 200

        body = response.json()

        for key in (
            "runtime",
            "metrics",
            "portfolio",
            "open_trades",
            "recent_closed_trades"
        ):

            assert key in body

    def test_dashboard_limits_recent_closed_trades_to_five(
        self,
        client
    ):

        for i in range(8):

            trade = trades_repository.create_trade(
                user_id=DEFAULT_USER_ID,
                symbol="BTCUSDT",
                action="BUY",
                entry_price=100.0,
                quantity=1.0,
                stop_loss=95.0,
                take_profit=110.0,
                trailing_stop=1.0
            )

            trades_repository.close_trade(
                trade_id=trade.id,
                exit_price=105.0,
                pnl=5.0,
                reason="TAKE_PROFIT"
            )

        response = client.get("/dashboard")

        body = response.json()

        assert len(body["recent_closed_trades"]) == 5


class TestSettingsEndpoint:

    @pytest.fixture(autouse=True)
    def _reset_settings_env(self):

        from core.config import settings_repository

        settings_repository.ENV_PATH.write_text(
            "MODE=paper\n"
            "BINANCE_TESTNET=true\n"
            "BINANCE_API_KEY=\n"
            "BINANCE_SECRET_KEY=\n"
        )

        yield

    def test_get_settings_returns_200(self, client):

        response = client.get("/settings")

        assert response.status_code == 200

        body = response.json()

        assert body["mode"] == "paper"

        assert body["allowed_modes"] == ["paper", "live"]

    def test_get_settings_never_leaks_real_key_values(self, client):

        response = client.get("/settings")

        body = response.json()

        assert "binance_api_key" not in body

        assert "binance_secret_key" not in body

    def test_put_settings_updates_testnet_keys(self, client):

        response = client.put(
            "/settings",
            json={
                "binance_testnet": True,
                "binance_api_key": "a" * 64,
                "binance_secret_key": "b" * 64
            }
        )

        assert response.status_code == 200

        body = response.json()

        assert body["binance_api_key_set"] is True

        assert body["binance_secret_key_set"] is True

        assert body["binance_testnet"] is True

    def test_put_settings_response_never_contains_raw_key(
        self,
        client
    ):

        secret_value = "c" * 64

        response = client.put(
            "/settings",
            json={"binance_api_key": secret_value}
        )

        assert secret_value not in response.text

    def test_put_settings_accepts_live_mode_and_restarts(
        self,
        client
    ):

        # a restart is only triggered when the runner was already
        # running (see apps/api/main.py) -- simulate that here
        with patch(
            "core.utils.runner_pid.read_runner_pid",
            return_value=4242
        ), patch(
            "core.services.process_manager_service._is_process_alive",
            return_value=True
        ), patch(
            "apps.api.main.restart_runner"
        ) as mock_restart:

            response = client.put(
                "/settings",
                json={"mode": "live"}
            )

        assert response.status_code == 200

        body = response.json()

        assert body["mode"] == "live"

        assert body["restart_triggered"] is True

        mock_restart.assert_called_once()

    def test_put_settings_rejects_invalid_key_length(self, client):

        response = client.put(
            "/settings",
            json={"binance_api_key": "too_short"}
        )

        assert response.status_code == 400

    def test_put_settings_partial_update_preserves_other_fields(
        self,
        client
    ):

        client.put(
            "/settings",
            json={
                "binance_api_key": "a" * 64,
                "binance_secret_key": "b" * 64
            }
        )

        response = client.put(
            "/settings",
            json={"binance_testnet": False}
        )

        body = response.json()

        assert body["binance_api_key_set"] is True

        assert body["binance_secret_key_set"] is True

        assert body["binance_testnet"] is False

    def test_put_settings_no_mode_change_does_not_restart(
        self,
        client
    ):

        with patch(
            "apps.api.main.restart_runner"
        ) as mock_restart:

            response = client.put(
                "/settings",
                json={"binance_testnet": False}
            )

        assert response.status_code == 200

        assert response.json()["restart_triggered"] is False

        mock_restart.assert_not_called()

    def test_put_settings_blocks_mode_change_with_open_position(
        self,
        client
    ):

        trade = trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        try:

            with patch(
                "apps.api.main.restart_runner"
            ) as mock_restart:

                response = client.put(
                    "/settings",
                    json={"mode": "live"}
                )

            assert response.status_code == 409

            assert "open" in response.json()["detail"].lower()

            mock_restart.assert_not_called()

        finally:

            from data.storage.database import SessionLocal

            from data.storage.models import Trade

            session = SessionLocal()

            session.query(Trade).filter(
                Trade.id == trade.id
            ).delete()

            session.commit()

            session.close()

    def test_put_settings_open_position_block_does_not_modify_env(
        self,
        client
    ):

        trade = trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        try:

            before = client.get("/settings").json()

            client.put(
                "/settings",
                json={"mode": "live"}
            )

            after = client.get("/settings").json()

            assert before["mode"] == after["mode"] == "paper"

        finally:

            from data.storage.database import SessionLocal

            from data.storage.models import Trade

            session = SessionLocal()

            session.query(Trade).filter(
                Trade.id == trade.id
            ).delete()

            session.commit()

            session.close()

    def test_put_settings_only_blocks_when_mode_is_in_payload(
        self,
        client
    ):

        # an open position must not block updates that don't touch
        # mode at all (e.g. rotating credentials while the bot is
        # actively running a position)
        trade = trades_repository.create_trade(
            user_id=DEFAULT_USER_ID,
            symbol="BTCUSDT",
            action="BUY",
            entry_price=100.0,
            quantity=1.0,
            stop_loss=95.0,
            take_profit=110.0,
            trailing_stop=1.0
        )

        try:

            response = client.put(
                "/settings",
                json={"binance_testnet": True}
            )

            assert response.status_code == 200

        finally:

            from data.storage.database import SessionLocal

            from data.storage.models import Trade

            session = SessionLocal()

            session.query(Trade).filter(
                Trade.id == trade.id
            ).delete()

            session.commit()

            session.close()

    def test_put_settings_restart_failure_returns_500(
        self,
        client
    ):

        from core.services.process_manager_service import (
            ProcessManagerError
        )

        # a restart is only triggered when the runner was already
        # running (see apps/api/main.py) -- simulate that here
        with patch(
            "core.utils.runner_pid.read_runner_pid",
            return_value=4242
        ), patch(
            "core.services.process_manager_service._is_process_alive",
            return_value=True
        ), patch(
            "apps.api.main.restart_runner",
            side_effect=ProcessManagerError(
                "simulated: process would not die"
            )
        ):

            response = client.put(
                "/settings",
                json={"mode": "live"}
            )

        assert response.status_code == 500

        assert "reiniciar" in response.json()["detail"].lower()


class TestApiTokenAuth:

    """
    apps/api/main.py's require_api_token dependency, applied to
    PUT /settings, POST /runner/start and POST /runner/stop.
    settings.API_ACCESS_TOKEN defaults to "" (auth disabled) --
    these tests explicitly patch it to exercise the enabled path.
    """

    @pytest.fixture(autouse=True)
    def _reset_settings_env(self):

        from core.config import settings_repository

        settings_repository.ENV_PATH.write_text(
            "MODE=paper\n"
            "BINANCE_TESTNET=true\n"
            "BINANCE_API_KEY=\n"
            "BINANCE_SECRET_KEY=\n"
        )

        yield

    def test_put_settings_without_token_is_rejected(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.put(
                "/settings",
                json={"account_balance": 200.0}
            )

        assert response.status_code == 401

    def test_put_settings_with_wrong_token_is_rejected(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.put(
                "/settings",
                json={"account_balance": 200.0},
                headers={"X-API-Token": "wrong-token"}
            )

        assert response.status_code == 401

    def test_put_settings_with_correct_token_succeeds(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.put(
                "/settings",
                json={"account_balance": 200.0},
                headers={"X-API-Token": "secret-token"}
            )

        assert response.status_code == 200

    def test_runner_start_without_token_is_rejected(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.post("/runner/start")

        assert response.status_code == 401

    def test_runner_stop_without_token_is_rejected(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.post("/runner/stop")

        assert response.status_code == 401

    def test_health_stays_open_even_with_token_configured(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.get("/health")

        assert response.status_code == 200

    def test_get_settings_stays_open_even_with_token_configured(
        self,
        client
    ):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            "secret-token"
        ):

            response = client.get("/settings")

        assert response.status_code == 200

    def test_no_token_configured_disables_auth(self, client):

        with patch.object(
            api_main.settings,
            "API_ACCESS_TOKEN",
            ""
        ):

            response = client.put(
                "/settings",
                json={"account_balance": 200.0}
            )

        assert response.status_code == 200

    def test_rate_limiter_is_wired_on_the_app(self):

        assert hasattr(app.state, "limiter")


class TestCors:

    def test_allows_vite_dev_origin(self, client):

        response = client.get(
            "/settings",
            headers={
                "Origin": "http://localhost:5173"
            }
        )

        assert (
            response.headers.get(
                "access-control-allow-origin"
            )
            == "http://localhost:5173"
        )


class TestJobHistoryAndEstimate:

    def test_history_can_be_filtered_by_job_type(self, client, tmp_path, monkeypatch):

        history_file = tmp_path / "jobs_history.json"
        history_file.write_text(
            json.dumps([
                {
                    "type": "optimizer",
                    "status": "done",
                    "started_at": 10,
                    "elapsed_seconds": 100,
                },
                {
                    "type": "backtest",
                    "status": "done",
                    "started_at": 20,
                    "elapsed_seconds": 80,
                },
            ]),
            encoding="utf-8",
        )

        monkeypatch.setattr(api_main, "_HISTORY_FILE", history_file)

        response = client.get("/jobs/history?jtype=optimizer&page=1")

        assert response.status_code == 200
        body = response.json()

        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["type"] == "optimizer"

    def test_estimate_returns_resource_snapshot(self, client):

        response = client.get("/jobs/estimate?jtype=backtest")

        assert response.status_code == 200
        body = response.json()

        assert "estimate_seconds" in body
        assert "profile" in body
        assert "hardware" in body

    def test_estimate_reflects_saved_symbols_without_restart(self, client):

        """
        core.config.settings.settings is a singleton read once at
        process import -- /jobs/estimate used to build its workload
        profile from that stale value instead of the .env file PUT
        /settings just wrote, so changing the symbol count in the
        Settings UI had no visible effect on the optimizer estimate
        until the whole API process was restarted.
        """

        from core.config import settings_repository

        settings_repository.update_settings(symbols="BTCUSDT")

        try:
            response = client.get("/jobs/estimate?jtype=optimizer&days=90")

            assert response.status_code == 200
            assert response.json()["profile"]["symbol_count"] == 1

        finally:
            settings_repository.update_settings(symbols="BTCUSDT,ETHUSDT")


class TestLiveBalance:

    def test_returns_paper_when_mode_is_not_live(self, client):

        with patch("apps.api.main.settings_repository.get_settings", return_value={"mode": "paper"}):
            response = client.get("/account/live-balance")

        assert response.status_code == 200
        assert response.json() == {
            "balance": None,
            "source": "paper",
            "error": None,
        }

    def test_uses_testnet_credentials_when_testnet_is_enabled(self, client):

        fake_client = AsyncMock()
        fake_client.get_account_info.return_value = {
            "balances": [
                {"asset": "USDT", "free": "123.45"},
                {"asset": "BTC", "free": "0.1"},
            ]
        }

        with patch("apps.api.main.settings_repository.get_settings", return_value={"mode": "live"}):
            with patch("core.config.settings_repository._read_raw_lines", return_value=[]):
                with patch(
                    "core.config.settings_repository._parse_current_values",
                    return_value={
                        "BINANCE_API_KEY": "key",
                        "BINANCE_SECRET_KEY": "secret",
                        "BINANCE_TESTNET": "true",
                        "LIVE_TRADING_CONFIRMED": "false",
                    },
                ):
                    with patch("core.services.binance_trading_client.BinanceTradingClient", return_value=fake_client) as mock_client:
                        response = client.get("/account/live-balance")

        assert response.status_code == 200
        body = response.json()
        assert body["balance"] == 123.45
        assert body["source"] == "binance_testnet"
        assert body["error"] is None
        mock_client.assert_called_once()
        assert mock_client.call_args.kwargs["testnet"] is True
        assert mock_client.call_args.kwargs["live_trading_confirmed"] is False

    def test_uses_mainnet_credentials_when_testnet_is_disabled(self, client):

        fake_client = AsyncMock()
        fake_client.get_account_info.return_value = {
            "balances": [
                {"asset": "USDT", "free": "50.00"},
            ]
        }

        with patch("apps.api.main.settings_repository.get_settings", return_value={"mode": "live"}):
            with patch("core.config.settings_repository._read_raw_lines", return_value=[]):
                with patch(
                    "core.config.settings_repository._parse_current_values",
                    return_value={
                        "BINANCE_API_KEY": "key",
                        "BINANCE_SECRET_KEY": "secret",
                        "BINANCE_TESTNET": "false",
                        "LIVE_TRADING_CONFIRMED": "true",
                    },
                ):
                    with patch("core.services.binance_trading_client.BinanceTradingClient", return_value=fake_client) as mock_client:
                        response = client.get("/account/live-balance")

        assert response.status_code == 200
        body = response.json()
        assert body["balance"] == 50.0
        assert body["source"] == "binance_mainnet"
        assert body["error"] is None
        mock_client.assert_called_once()
        assert mock_client.call_args.kwargs["testnet"] is False
        assert mock_client.call_args.kwargs["live_trading_confirmed"] is True


class TestRunnerStartBalanceValidation:

    def test_runner_start_blocks_when_balance_is_insufficient(self, client):

        with patch(
            "apps.api.main.build_startup_balance_report",
            return_value={
                "allowed": False,
                "reason": "Saldo insuficiente",
            }
        ):
            response = client.post("/runner/start")

        assert response.status_code == 409
        assert response.json()["detail"] == "Saldo insuficiente"

    def test_runner_start_check_returns_report(self, client):

        with patch(
            "apps.api.main.build_startup_balance_report",
            return_value={
                "allowed": True,
                "current_balance": 100.0,
                "required_balance_single_trade": 42.0,
                "required_balance_max_positions": 84.0,
                "shortfall": 0.0,
                "source": "paper",
                "symbols": [],
                "reason": None,
            }
        ):
            response = client.get("/runner/start-check")

        assert response.status_code == 200
        body = response.json()
        assert body["allowed"] is True
        assert body["required_balance_single_trade"] == 42.0
