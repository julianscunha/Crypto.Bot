# -*- coding: utf-8 -*-

import subprocess
import sys

from pathlib import Path

from core.utils.console_logger import (
    log
)

# =====================================================
# ROOT
# =====================================================

ROOT = Path(__file__).resolve().parent.parent.parent

REQUIREMENTS_FILE = (
    ROOT
    / "scripts"
    / "bootstrap"
    / "requirements.txt"
)

# =====================================================
# STATUS LINE
# =====================================================

def status_line(label, value):

    return f"{label:.<30} {value}"

# =====================================================
# INSTALL REQUIREMENTS
# =====================================================

def install_requirements():

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(REQUIREMENTS_FILE),
                "--disable-pip-version-check"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            with open(
                ROOT / "logs" / "bootstrap.log",
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    result.stderr
                )

            log(
                "SYSTEM",
                status_line(
                    "Dependencies",
                    "FAILED"
                ),
                "ERROR"
            )

            return False

        log(
            "SYSTEM",
            status_line(
                "Dependencies",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    except Exception as error:

        with open(
            ROOT / "logs" / "bootstrap.log",
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"{str(error)}\n"
            )

        log(
            "SYSTEM",
            status_line(
                "Dependencies",
                "FAILED"
            ),
            "ERROR"
        )

        return False

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    install_requirements()