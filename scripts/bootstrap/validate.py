# -*- coding: utf-8 -*-

import sys

from pathlib import Path

from core.utils.console_logger import (
    log
)

# =====================================================
# ROOT
# =====================================================

ROOT = Path(__file__).resolve().parent.parent.parent

# =====================================================
# FILES
# =====================================================

FILE_PATHS = {
    ".env": ROOT / ".env",
    "requirements.txt": (
        ROOT
        / "scripts"
        / "bootstrap"
        / "requirements.txt"
    )
}

# =====================================================
# PYTHON VERSION
# =====================================================

MIN_PYTHON = (3, 11)

# =====================================================
# STATUS LINE
# =====================================================

def status_line(label, value):

    return f"{label:.<30} {value}"

# =====================================================
# VALIDATE PYTHON
# =====================================================

def validate_python():

    success = (
        sys.version_info >= MIN_PYTHON
    )

    if success:

        log(
            "SYSTEM",
            status_line(
                "Python",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    log(
        "SYSTEM",
        status_line(
            "Python",
            "FAILED"
        ),
        "ERROR"
    )

    return False

# =====================================================
# VALIDATE STRUCTURE
# =====================================================

def validate_structure():

    required = [
        ROOT / "apps",
        ROOT / "core",
        ROOT / "data",
        ROOT / "scripts"
    ]

    success = all(
        path.exists()
        for path in required
    )

    if success:

        log(
            "SYSTEM",
            status_line(
                "Structure",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    log(
        "SYSTEM",
        status_line(
            "Structure",
            "FAILED"
        ),
        "ERROR"
    )

    return False

# =====================================================
# VALIDATE FILES
# =====================================================

def validate_files():

    success = True

    for _, full_path in FILE_PATHS.items():

        if not full_path.exists():

            success = False

    if success:

        log(
            "SYSTEM",
            status_line(
                "Files",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    log(
        "SYSTEM",
        status_line(
            "Files",
            "FAILED"
        ),
        "ERROR"
    )

    return False

# =====================================================
# VALIDATE VENV
# =====================================================

def validate_venv():

    venv_path = ROOT / ".venv"

    if not venv_path.exists():

        log(
            "SYSTEM",
            status_line(
                "VirtualEnv",
                "WARNING"
            ),
            "WARNING"
        )

        return

    log(
        "SYSTEM",
        status_line(
            "VirtualEnv",
            "OK"
        ),
        "SUCCESS"
    )

# =====================================================
# MAIN VALIDATION
# =====================================================

def validate_environment():

    validations = [
        validate_python(),
        validate_structure(),
        validate_files()
    ]

    validate_venv()

    if all(validations):

        log(
            "SYSTEM",
            status_line(
                "Environment",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    log(
        "SYSTEM",
        status_line(
            "Environment",
            "FAILED"
        ),
        "ERROR"
    )

    return False

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    validate_environment()