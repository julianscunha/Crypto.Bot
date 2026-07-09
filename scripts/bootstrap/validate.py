# -*- coding: utf-8 -*-

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

# =====================================================
# FILES
# =====================================================

FILE_PATHS = {

    ".env":
        ROOT / ".env",

    "requirements.txt":
        (
            ROOT
            / "scripts"
            / "bootstrap"
            / "requirements.txt"
        )
}

# =====================================================
# PYTHON
# =====================================================

MIN_PYTHON = (
    3,
    11
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
# PYTHON VALIDATION
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
# STRUCTURE VALIDATION
# =====================================================

def validate_structure():

    required_paths = [

        ROOT / "apps",

        ROOT / "core",

        ROOT / "data",

        ROOT / "scripts"
    ]

    success = all(

        path.exists()

        for path in required_paths
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
# FILE VALIDATION
# =====================================================

def validate_files():

    missing_files = []

    for name, path in FILE_PATHS.items():

        if not path.exists():

            missing_files.append(
                name
            )

    if not missing_files:

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
# VENV VALIDATION
# =====================================================

def validate_venv():

    venv_path = (
        ROOT / ".venv"
    )

    if venv_path.exists():

        log(
            "SYSTEM",
            status_line(
                "VirtualEnv",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    log(
        "SYSTEM",
        status_line(
            "VirtualEnv",
            "WARNING"
        ),
        "WARNING"
    )

    return False

# =====================================================
# FRONTEND VALIDATION
# =====================================================
#
# Informational only, like validate_venv(): the frontend is on the
# roadmap (see docs/README_FULL.md) and not built yet in this project, so
# its absence must never fail validate_environment() or block
# startup. This just surfaces the status proactively at boot instead
# of only discovering it when menu option [4]/[5] is selected.

def validate_frontend():

    frontend_path = (
        ROOT / "frontend"
    )

    if frontend_path.exists():

        log(
            "SYSTEM",
            status_line(
                "Frontend",
                "OK"
            ),
            "SUCCESS"
        )

        return True

    log(
        "SYSTEM",
        status_line(
            "Frontend",
            "NOT_BUILT_YET"
        ),
        "WARNING"
    )

    return False

# =====================================================
# ENVIRONMENT VALIDATION
# =====================================================

def validate_environment():

    validations = [

        validate_python(),

        validate_structure(),

        validate_files()
    ]

    validate_venv()

    validate_frontend()

    success = all(
        validations
    )

    if success:

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
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    validate_environment()
