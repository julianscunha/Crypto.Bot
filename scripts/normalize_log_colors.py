# -*- coding: utf-8 -*-

from pathlib import Path


SEARCH_DIRS = [
    "core",
    "data",
    "apps"
]


KEYWORDS = [
    "[KLINE]",
    "[MARKET]",
    "[EMA]",
    "[STRATEGY]",
    "[STRUCTURE",
    "[SIGNAL]",
    "[RISK]",
    "[EXECUTION]",
    "[POSITION]",
    "[BINANCE]"
]


def main():

    found = 0

    for folder in SEARCH_DIRS:

        for path in Path(folder).rglob("*.py"):

            try:

                content = path.read_text(
                    encoding="utf-8"
                )

            except Exception:
                continue

            for keyword in KEYWORDS:

                if keyword in content:

                    print(
                        f"[FOUND] "
                        f"{path} "
                        f"-> {keyword}"
                    )

                    found += 1

    print()

    print(
        f"[OK] Total matches: {found}"
    )


if __name__ == "__main__":

    main()