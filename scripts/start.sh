#!/usr/bin/env bash
# ============================================================
# CRYPTO.BOT STARTUP
# ============================================================

set -uo pipefail

echo ""
echo "============================================================"
echo "                    CRYPTO.BOT ENGINE"
echo "============================================================"
echo ""

# ============================================================
# ROOT
# ============================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT"

# ============================================================
# START
# ============================================================
#
# Delegates to the same interactive launcher used by start.ps1
# (scripts/bootstrap/launcher.py), which validates the environment,
# installs dependencies from scripts/bootstrap/requirements.txt, and
# shows the runtime menu (Runner / Optimizer / Backtest / Frontend /
# Full Stack). Keeping both platform scripts as thin wrappers around
# the same launcher avoids the two diverging out of sync.

python3 -m scripts.bootstrap.launcher
LAUNCHER_EXIT_CODE=$?

echo ""
echo "============================================================"
echo "                 ENGINE STOPPED"
echo "============================================================"
echo ""

exit $LAUNCHER_EXIT_CODE
