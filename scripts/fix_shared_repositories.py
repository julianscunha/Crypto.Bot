# -*- coding: utf-8 -*-

from pathlib import Path


FILES = {

    # =====================================================
    # TRADES REPOSITORY
    # =====================================================

    "data/storage/repositories/trades_repository.py": {

        "append": (
            "\n\n"
            "trades_repository = "
            "TradesRepository()\n"
        ),

        "replacements": []
    },

    # =====================================================
    # RISK AGENT
    # =====================================================

    "core/agents/risk_agent.py": {

        "append": "",

        "replacements": [

            (
                "from data.storage.repositories.trades_repository import (\n"
                "    TradesRepository\n"
                ")",

                "from data.storage.repositories.trades_repository import (\n"
                "    trades_repository\n"
                ")"
            ),

            (
                "self.positions = TradesRepository()",

                "self.positions = trades_repository"
            )
        ]
    },

    # =====================================================
    # EXECUTION AGENT
    # =====================================================

    "core/agents/execution_agent.py": {

        "append": "",

        "replacements": [

            (
                "from data.storage.repositories.trades_repository import (\n"
                "    TradesRepository\n"
                ")",

                "from data.storage.repositories.trades_repository import (\n"
                "    trades_repository\n"
                ")"
            ),

            (
                "self.positions = TradesRepository()",

                "self.positions = trades_repository"
            )
        ]
    },

    # =====================================================
    # POSITION MANAGER AGENT
    # =====================================================

    "core/agents/position_manager_agent.py": {

        "append": "",

        "replacements": [

            (
                "from data.storage.repositories.trades_repository import (\n"
                "    TradesRepository\n"
                ")",

                "from data.storage.repositories.trades_repository import (\n"
                "    trades_repository\n"
                ")"
            ),

            (
                "self.positions = TradesRepository()",

                "self.positions = trades_repository"
            )
        ]
    },

    # =====================================================
    # PORTFOLIO AGENT
    # =====================================================

    "core/agents/portfolio_agent.py": {

        "append": "",

        "replacements": [

            (
                "from data.storage.repositories.trades_repository import (\n"
                "    TradesRepository\n"
                ")",

                "from data.storage.repositories.trades_repository import (\n"
                "    trades_repository\n"
                ")"
            ),

            (
                "self.positions = TradesRepository()",

                "self.positions = trades_repository"
            )
        ]
    }
}


def process_file(path, config):

    file_path = Path(path)

    if not file_path.exists():

        print(
            f"[ERROR] Missing: {path}"
        )

        return

    content = file_path.read_text(
        encoding="utf-8"
    )

    # =====================================================
    # REPLACEMENTS
    # =====================================================

    for old, new in config["replacements"]:

        if old in content:

            content = content.replace(
                old,
                new
            )

            print(
                f"[OK] Updated: {path}"
            )

    # =====================================================
    # APPEND SINGLETON
    # =====================================================

    append_text = config["append"]

    if append_text:

        singleton_line = (
            append_text.strip()
        )

        if singleton_line not in content:

            content += append_text

            print(
                f"[OK] Singleton added: {path}"
            )

    file_path.write_text(
        content,
        encoding="utf-8"
    )


def main():

    print()

    print(
        "=" * 60
    )

    print(
        " FIX SHARED REPOSITORIES "
    )

    print(
        "=" * 60
    )

    print()

    for path, config in FILES.items():

        process_file(
            path,
            config
        )

    print()

    print(
        "=" * 60
    )

    print(
        "[OK] SHARED REPOSITORIES READY"
    )

    print(
        "=" * 60
    )

    print()


if __name__ == "__main__":

    main()