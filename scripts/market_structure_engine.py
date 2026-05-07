# -*- coding: utf-8 -*-

import os


FILES = [
    "core/services/market_structure_service.py",
    "core/config/market_structure_config.py"
]


def validate():

    for file in FILES:

        if not os.path.exists(file):

            print(f"[ERROR] Missing: {file}")

            return

    print("[OK] Market Structure Engine validated")


if __name__ == "__main__":

    validate()