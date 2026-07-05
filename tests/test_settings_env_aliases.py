# -*- coding: utf-8 -*-

"""
Regression tests for core/config/settings.py's env_int_aliased()

Bug fixed: MINIMUM_STRUCTURE_CANDLES (used by core/config/
trading_config.py) and STRUCTURE_MIN_CANDLES (used by core/config/
market_structure_config.py, the config MarketStructureService
actually reads) represent the same setting but were read from two
different, non-overlapping env var names. A person setting a third,
equally reasonable variant (MIN_STRUCTURE_CANDLES) in .env had it
silently ignored -- the system kept using the 20-candle default with
no error or warning anywhere, and every signal stayed gated behind
ATR/structure warmup far longer than intended.
"""

import os

import pytest

from core.config.settings import (
    env_int,
    env_int_aliased
)


ENV_VAR_NAMES = (
    "TEST_ALIAS_A",
    "TEST_ALIAS_B",
    "TEST_ALIAS_C"
)


@pytest.fixture(autouse=True)
def _clear_test_env_vars():

    for key in ENV_VAR_NAMES:

        os.environ.pop(key, None)

    yield

    for key in ENV_VAR_NAMES:

        os.environ.pop(key, None)


class TestEnvIntAliased:

    def test_returns_default_when_none_of_the_aliases_are_set(self):

        result = env_int_aliased(
            ENV_VAR_NAMES,
            99
        )

        assert result == 99

    def test_uses_value_from_any_recognized_alias(self):

        os.environ["TEST_ALIAS_C"] = "6"

        result = env_int_aliased(
            ENV_VAR_NAMES,
            20
        )

        assert result == 6

    def test_first_alias_takes_priority_when_multiple_are_set(self):

        os.environ["TEST_ALIAS_A"] = "42"

        os.environ["TEST_ALIAS_C"] = "6"

        result = env_int_aliased(
            ENV_VAR_NAMES,
            20
        )

        assert result == 42

    def test_minimum_clamp_still_applies(self):

        os.environ["TEST_ALIAS_A"] = "1"

        result = env_int_aliased(
            ENV_VAR_NAMES,
            20,
            minimum=5
        )

        assert result == 5

    def test_maximum_clamp_still_applies(self):

        os.environ["TEST_ALIAS_A"] = "999"

        result = env_int_aliased(
            ENV_VAR_NAMES,
            20,
            maximum=100
        )

        assert result == 100

    def test_invalid_value_on_matched_alias_falls_back_to_default(
        self
    ):

        os.environ["TEST_ALIAS_A"] = "not_a_number"

        result = env_int_aliased(
            ENV_VAR_NAMES,
            20
        )

        assert result == 20

    def test_behaves_like_env_int_with_a_single_key(self):

        os.environ["TEST_ALIAS_A"] = "7"

        aliased_result = env_int_aliased(
            ("TEST_ALIAS_A",),
            20,
            minimum=5
        )

        plain_result = env_int(
            "TEST_ALIAS_A",
            20,
            minimum=5
        )

        assert aliased_result == plain_result == 7


class TestStructureMinCandlesNamingFix:

    """
    Exercises the real MINIMUM_STRUCTURE_CANDLES / STRUCTURE_MIN_CANDLES
    settings end to end via core.config.trading_config and
    core.config.market_structure_config, reloading them fresh each
    test so changes to os.environ are actually picked up (these
    modules read settings.py's class attributes at import time).
    """

    @pytest.fixture(autouse=True)
    def _clear_structure_env_vars(self):

        names = (
            "MINIMUM_STRUCTURE_CANDLES",
            "STRUCTURE_MIN_CANDLES",
            "MIN_STRUCTURE_CANDLES"
        )

        originals = {
            name: os.environ.get(name)
            for name in names
        }

        for name in names:

            os.environ.pop(name, None)

        yield

        for name, value in originals.items():

            if value is None:

                os.environ.pop(name, None)

            else:

                os.environ[name] = value

    @staticmethod
    def _reloaded_structure_candle_values():

        import importlib

        import core.config.settings as settings_module

        import core.config.trading_config as trading_config_module

        import core.config.market_structure_config as \
            market_structure_config_module

        importlib.reload(settings_module)

        importlib.reload(trading_config_module)

        importlib.reload(market_structure_config_module)

        return (
            trading_config_module.TRADING_CONFIG[
                "minimum_structure_candles"
            ],

            market_structure_config_module.MARKET_STRUCTURE_CONFIG[
                "minimum_structure_candles"
            ]
        )

    def test_min_structure_candles_alias_is_recognized(self):

        # this is the exact variable name that previously had no
        # effect at all
        os.environ["MIN_STRUCTURE_CANDLES"] = "6"

        trading_value, structure_value = (
            self._reloaded_structure_candle_values()
        )

        assert trading_value == 6

        assert structure_value == 6

    def test_both_configs_agree_using_the_canonical_names_too(self):

        os.environ["MINIMUM_STRUCTURE_CANDLES"] = "8"

        os.environ["STRUCTURE_MIN_CANDLES"] = "8"

        trading_value, structure_value = (
            self._reloaded_structure_candle_values()
        )

        assert trading_value == 8

        assert structure_value == 8

    def test_default_is_20_when_nothing_is_set(self):

        # explicitly override the value load_dotenv() would
        # otherwise repopulate from the real .env (which may
        # legitimately set MIN_STRUCTURE_CANDLES) -- this test
        # specifically wants to verify the no-override fallback,
        # not depend on whatever the real .env happens to contain
        os.environ["MIN_STRUCTURE_CANDLES"] = ""

        os.environ.pop("MIN_STRUCTURE_CANDLES", None)

        import dotenv

        original_load_dotenv = dotenv.load_dotenv

        dotenv.load_dotenv = lambda *args, **kwargs: None

        try:

            trading_value, structure_value = (
                self._reloaded_structure_candle_values()
            )

        finally:

            dotenv.load_dotenv = original_load_dotenv

        assert trading_value == 20

        assert structure_value == 20


class TestMaxOpenPositionsNamingFix:

    """
    Bug fixed: SIGNAL_QUALITY_CONFIG["maximum_open_positions"] (the
    config SignalQualityService._validate_position_limit actually
    enforces) read getattr(settings, "MAXIMUM_OPEN_POSITIONS", 3) --
    but settings.py never defined a MAXIMUM_OPEN_POSITIONS attribute
    at all, only MAX_OPEN_POSITIONS. The getattr always silently fell
    back to its 3-position default, regardless of what a person set.

    Real-world impact confirmed during this audit: the project's own
    .env had MAX_OPEN_POSITIONS=2 set, believing it capped the bot at
    2 simultaneous positions. It had zero effect -- the bot was
    actually enforcing the 3-position default the whole time, a real
    difference in risk exposure the operator didn't know about.
    """

    @pytest.fixture(autouse=True)
    def _clear_position_limit_env_vars(self):

        names = (
            "MAX_OPEN_POSITIONS",
            "MAXIMUM_OPEN_POSITIONS"
        )

        originals = {
            name: os.environ.get(name)
            for name in names
        }

        for name in names:

            os.environ.pop(name, None)

        yield

        for name, value in originals.items():

            if value is None:

                os.environ.pop(name, None)

            else:

                os.environ[name] = value

    @staticmethod
    def _reloaded_max_open_positions():

        import importlib

        import core.config.settings as settings_module

        import core.config.signal_quality_config as \
            signal_quality_config_module

        importlib.reload(settings_module)

        importlib.reload(signal_quality_config_module)

        return (
            signal_quality_config_module
            .SIGNAL_QUALITY_CONFIG[
                "maximum_open_positions"
            ]
        )

    def test_max_open_positions_env_var_is_now_respected(self):

        # this is the exact scenario found in the real .env: setting
        # MAX_OPEN_POSITIONS previously had zero effect on enforcement
        os.environ["MAX_OPEN_POSITIONS"] = "2"

        assert self._reloaded_max_open_positions() == 2

    def test_maximum_open_positions_alias_also_works(self):

        os.environ["MAXIMUM_OPEN_POSITIONS"] = "5"

        # the real .env may also set MAX_OPEN_POSITIONS (it does, in
        # this project) -- disable load_dotenv() so that real file
        # doesn't override the alias value this test is injecting
        # directly via os.environ
        import dotenv

        original_load_dotenv = dotenv.load_dotenv

        dotenv.load_dotenv = lambda *args, **kwargs: None

        try:

            result = self._reloaded_max_open_positions()

        finally:

            dotenv.load_dotenv = original_load_dotenv

        assert result == 5

    def test_default_is_3_when_nothing_is_set(self):

        import dotenv

        original_load_dotenv = dotenv.load_dotenv

        dotenv.load_dotenv = lambda *args, **kwargs: None

        try:

            result = self._reloaded_max_open_positions()

        finally:

            dotenv.load_dotenv = original_load_dotenv

        assert result == 3
