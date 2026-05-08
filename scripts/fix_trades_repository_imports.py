# -*- coding: utf-8 -*-

from pathlib import Path


ROOT = Path(".")


OLD_IMPORTS = [

    (
        "from data.storage.repositories.trades_repository import (",
        "from data.storage.repositories.trades_repository import ("
    ),

    (
        "from data.storage.repositories.trades_repository import",
        "from data.storage.repositories.trades_repository import"
    )
]


def process_file(path: Path):

    try:

        content = path.read_text(
            encoding="utf-8"
        )

    except Exception:

        return

    original = content

    for old, new in OLD_IMPORTS:

        content = content.replace(
            old,
            new
        )

    if content != original:

        path.write_text(
            content,
            encoding="utf-8"
        )

        print(
            f"[OK] Fixed imports: {path}"
        )


def main():

    print()

    print("=" * 60)

    print(" FIX TRADES REPOSITORY IMPORTS ")

    print("=" * 60)

    print()

    for path in ROOT.rglob("*.py"):

        process_file(path)

    print()

    print("=" * 60)

    print("[OK] IMPORTS NORMALIZED")

    print("=" * 60)

    print()


if __name__ == "__main__":

    main()