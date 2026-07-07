# -*- coding: utf-8 -*-

"""
Regression tests for scripts/bootstrap/bootstrap.py

Bug fixed: write_bootstrap_log() opened ROOT/"logs"/"bootstrap.log"
in append mode without first ensuring logs/ exists. On a fresh
checkout without that directory, a pip install failure would be
masked by a second, more confusing FileNotFoundError instead of the
actual dependency error.
"""

from scripts.bootstrap.bootstrap import (
    write_bootstrap_log
)


class TestWriteBootstrapLog:

    def test_creates_logs_directory_if_missing(self, tmp_path, monkeypatch):

        fake_log_path = (
            tmp_path / "logs" / "bootstrap.log"
        )

        monkeypatch.setattr(
            "scripts.bootstrap.bootstrap.BOOTSTRAP_LOG",
            fake_log_path
        )

        assert not fake_log_path.parent.exists()

        write_bootstrap_log("test entry")

        assert fake_log_path.exists()

        assert "test entry" in fake_log_path.read_text()

    def test_appends_without_raising_when_directory_exists(
        self,
        tmp_path,
        monkeypatch
    ):

        fake_log_path = (
            tmp_path / "logs" / "bootstrap.log"
        )

        fake_log_path.parent.mkdir(parents=True)

        monkeypatch.setattr(
            "scripts.bootstrap.bootstrap.BOOTSTRAP_LOG",
            fake_log_path
        )

        write_bootstrap_log("first")

        write_bootstrap_log("second")

        content = fake_log_path.read_text()

        assert "first" in content

        assert "second" in content
