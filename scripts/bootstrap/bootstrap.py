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

ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

REQUIREMENTS_FILE = (
    ROOT
    / "scripts"
    / "bootstrap"
    / "requirements.txt"
)

BOOTSTRAP_LOG = (
    ROOT
    / "logs"
    / "bootstrap.log"
)

# =====================================================
# STATUS
# =====================================================

def status_line(
    label,
    value
):

    return (
        f"{label:.<30} {value}"
    )

# =====================================================
# WRITE LOG
# =====================================================

def write_bootstrap_log(
    content: str
):

    with open(
        BOOTSTRAP_LOG,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            f"{content}\n"
        )

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

                str(
                    REQUIREMENTS_FILE
                ),

                "--disable-pip-version-check"
            ],

            capture_output=True,

            text=True
        )

        # =================================================
        # FAILURE
        # =================================================

        if result.returncode != 0:

            write_bootstrap_log(
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

        # =================================================
        # SUCCESS
        # =================================================

        log(
            "SYSTEM",
            status_line(
                "Dependencies",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    # =====================================================
    # EXCEPTION
    # =====================================================

    except Exception as error:

        write_bootstrap_log(
            str(error)
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
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    install_requirements()