# -*- coding: utf-8 -*-

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def ensure():

    requirements = ROOT / "requirements.txt"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("[OK]  Environment ready")


if __name__ == "__main__":
    ensure()