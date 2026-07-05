# -*- coding: utf-8 -*-

"""
Unit tests for core/config/settings_repository.py

The autouse _isolated_settings_env fixture in conftest.py redirects
ENV_PATH to a temp file for the whole test session, so these tests
never touch the user's real .env / Binance credentials.
"""

import pytest

from core.config import settings_repository


@pytest.fixture(autouse=True)
def _reset_env_file():

    """
    Reset the isolated .env back to a known baseline before each
    test in this file, so tests don't leak state into one another.
    """

    settings_repository.ENV_PATH.write_text(
        "MODE=paper\n"
        "BINANCE_TESTNET=true\n"
        "BINANCE_API_KEY=\n"
        "BINANCE_SECRET_KEY=\n"
    )

    yield


class TestGetSettings:

    def test_returns_paper_mode_by_default(self):

        result = settings_repository.get_settings()

        assert result["mode"] == "paper"

    def test_allowed_modes_includes_paper_and_live(self):

        result = settings_repository.get_settings()

        assert result["allowed_modes"] == ["paper", "live"]

    def test_live_trading_marked_unavailable(self):

        result = settings_repository.get_settings()

        assert result["live_trading_available"] is False

        assert len(
            result["live_trading_unavailable_reason"]
        ) > 0

    def test_no_keys_set_initially(self):

        result = settings_repository.get_settings()

        assert result["binance_api_key_set"] is False

        assert result["binance_secret_key_set"] is False

        assert result["binance_api_key_masked"] == ""

        assert result["binance_secret_key_masked"] == ""

    def test_missing_env_file_does_not_raise(self, monkeypatch):

        from pathlib import Path

        monkeypatch.setattr(
            settings_repository,
            "ENV_PATH",
            Path("/tmp/does_not_exist_crypto_bot_test.env")
        )

        result = settings_repository.get_settings()

        assert result["mode"] == "paper"


class TestLiveTradingAvailability:

    """
    live_trading_available requires BOTH Binance credentials set AND
    LIVE_TRADING_CONFIRMED=true -- neither alone is sufficient. This
    mirrors core/services/binance_trading_client.py's own gate
    (testnet=False requires live_trading_confirmed=True explicitly).
    """

    def test_unavailable_with_no_credentials_and_no_confirmation(
        self
    ):

        result = settings_repository.get_settings()

        assert result["live_trading_available"] is False

        assert "API key and secret" in (
            result["live_trading_unavailable_reason"]
        )

    def test_unavailable_with_credentials_but_no_confirmation(
        self
    ):

        settings_repository.update_settings(
            binance_api_key="A" * 64,
            binance_secret_key="B" * 64
        )

        result = settings_repository.get_settings()

        assert result["live_trading_available"] is False

        assert "LIVE_TRADING_CONFIRMED" in (
            result["live_trading_unavailable_reason"]
        )

    def test_unavailable_with_confirmation_but_no_credentials(
        self
    ):

        settings_repository._write_raw_lines(
            settings_repository._read_raw_lines()
            +
            ["LIVE_TRADING_CONFIRMED=true\n"]
        )

        result = settings_repository.get_settings()

        assert result["live_trading_available"] is False

        assert "API key and secret" in (
            result["live_trading_unavailable_reason"]
        )

    def test_available_with_both_credentials_and_confirmation(
        self
    ):

        settings_repository.update_settings(
            binance_api_key="A" * 64,
            binance_secret_key="B" * 64
        )

        settings_repository._write_raw_lines(
            settings_repository._read_raw_lines()
            +
            ["LIVE_TRADING_CONFIRMED=true\n"]
        )

        result = settings_repository.get_settings()

        assert result["live_trading_available"] is True

        assert result["live_trading_unavailable_reason"] is None


class TestUpdateSettingsKeys:

    def test_setting_valid_key_marks_it_set(self):

        settings_repository.update_settings(
            binance_api_key="a" * 64
        )

        result = settings_repository.get_settings()

        assert result["binance_api_key_set"] is True

        assert result["binance_api_key_masked"] != ""

    def test_masked_value_never_contains_real_key(self):

        secret = "f" * 64

        settings_repository.update_settings(
            binance_secret_key=secret
        )

        result = settings_repository.get_settings()

        assert secret not in str(result)

    def test_empty_string_clears_key(self):

        settings_repository.update_settings(
            binance_api_key="a" * 64
        )

        settings_repository.update_settings(
            binance_api_key=""
        )

        result = settings_repository.get_settings()

        assert result["binance_api_key_set"] is False

    def test_wrong_length_key_is_rejected(self):

        with pytest.raises(
            settings_repository.SettingsValidationError
        ):

            settings_repository.update_settings(
                binance_api_key="too_short"
            )

    def test_wrong_length_secret_is_rejected(self):

        with pytest.raises(
            settings_repository.SettingsValidationError
        ):

            settings_repository.update_settings(
                binance_secret_key="x" * 30
            )

    def test_updating_one_field_does_not_clear_others(self):

        settings_repository.update_settings(
            binance_api_key="a" * 64,
            binance_secret_key="b" * 64
        )

        settings_repository.update_settings(
            binance_testnet=False
        )

        result = settings_repository.get_settings()

        assert result["binance_api_key_set"] is True

        assert result["binance_secret_key_set"] is True

        assert result["binance_testnet"] is False


class TestUpdateSettingsMode:

    def test_explicit_paper_mode_is_accepted(self):

        result = settings_repository.update_settings(
            mode="paper"
        )

        assert result["mode"] == "paper"

    def test_live_mode_is_accepted(self):

        # "live" is a valid MODE value -- the actual safety gate
        # (LIVE_TRADING_CONFIRMED) is enforced separately by
        # core/services/binance_trading_client.py, not by this
        # validation, since MODE alone must never be enough to
        # reach mainnet (see that module's docstring)
        settings_repository.update_settings(
            mode="live"
        )

        result = settings_repository.get_settings()

        assert result["mode"] == "live"

    def test_unknown_mode_is_rejected(self):

        with pytest.raises(
            settings_repository.SettingsValidationError
        ):

            settings_repository.update_settings(
                mode="turbo"
            )

    def test_rejected_mode_does_not_modify_file(self):

        before = settings_repository.get_settings()

        try:

            settings_repository.update_settings(
                mode="turbo"
            )

        except settings_repository.SettingsValidationError:

            pass

        after = settings_repository.get_settings()

        assert before["mode"] == after["mode"]


class TestFileFormatPreservation:

    def test_preserves_comments_and_other_keys(self):

        settings_repository.ENV_PATH.write_text(
            "# comment line\n"
            "\n"
            "MODE=paper\n"
            "\n"
            "ACCOUNT_BALANCE=100.0\n"
            "BINANCE_TESTNET=true\n"
            "BINANCE_API_KEY=\n"
            "BINANCE_SECRET_KEY=\n"
        )

        settings_repository.update_settings(
            binance_api_key="a" * 64
        )

        content = settings_repository.ENV_PATH.read_text()

        assert "# comment line" in content

        assert "ACCOUNT_BALANCE=100.0" in content

    def test_appends_key_if_missing_from_file(self):

        settings_repository.ENV_PATH.write_text(
            "MODE=paper\n"
        )

        settings_repository.update_settings(
            binance_api_key="a" * 64
        )

        content = settings_repository.ENV_PATH.read_text()

        assert "BINANCE_API_KEY=" + ("a" * 64) in content

    def test_idempotent_round_trip(self):

        settings_repository.update_settings(
            binance_testnet=True,
            binance_api_key="a" * 64,
            binance_secret_key="b" * 64
        )

        first_read = settings_repository.get_settings()

        settings_repository.update_settings(
            binance_testnet=True
        )

        second_read = settings_repository.get_settings()

        assert first_read == second_read
