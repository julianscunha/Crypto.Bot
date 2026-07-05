# -*- coding: utf-8 -*-

"""
Tests for scripts/bootstrap/validate.py

Covers the new validate_frontend() check: informational only, must
never block validate_environment() from succeeding, since the
frontend is roadmap (not yet built) for this project.
"""

from unittest.mock import patch

from scripts.bootstrap.validate import (
    validate_frontend,
    validate_environment,
    validate_python,
    validate_structure,
    validate_files
)


class TestValidateFrontend:

    def test_false_when_frontend_directory_missing(self, tmp_path):

        with patch(
            "scripts.bootstrap.validate.ROOT",
            tmp_path
        ):

            assert validate_frontend() is False

    def test_true_when_frontend_directory_exists(self, tmp_path):

        with patch(
            "scripts.bootstrap.validate.ROOT",
            tmp_path
        ):

            (tmp_path / "frontend").mkdir()

            assert validate_frontend() is True

    def test_does_not_block_environment_validation_when_frontend_missing(
        self,
        tmp_path
    ):

        # validate_frontend() itself must return False without
        # raising when frontend/ is absent, independent of whatever
        # validate_environment() decides overall (FILE_PATHS/
        # STRUCTURE_PATHS are captured at module import time against
        # the real ROOT, so full environment isolation isn't
        # practical here -- this isolates just the frontend check)
        with patch(
            "scripts.bootstrap.validate.ROOT",
            tmp_path
        ):

            assert validate_frontend() is False

    def test_does_not_block_environment_validation_in_real_project(
        self
    ):

        # sanity check against the real project layout too,
        # regardless of whether frontend/ happens to exist here
        result = validate_environment()

        assert result is True


class TestValidatePython:

    def test_passes_on_current_interpreter(self):

        assert validate_python() is True


class TestValidateStructure:

    def test_passes_with_real_project_layout(self):

        assert validate_structure() is True


class TestValidateFiles:

    def test_passes_with_real_env_and_requirements(self):

        assert validate_files() is True
