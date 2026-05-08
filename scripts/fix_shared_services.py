# -*- coding: utf-8 -*-

from pathlib import Path


FILES = {

    # =====================================================
    # ATR SERVICE
    # =====================================================

    "core/services/atr_service.py": {

        "append": "\n\natr_service = AtrService()\n",

        "replacements": []
    },

    # =====================================================
    # EMA SERVICE
    # =====================================================

    "core/services/ema_trend_service.py": {

        "append": "\n\nema_trend_service = EmaTrendService()\n",

        "replacements": []
    },

    # =====================================================
    # MARKET STRUCTURE SERVICE
    # =====================================================

    "core/services/market_structure_service.py": {

        "append": (
            "\n\n"
            "market_structure_service = "
            "MarketStructureService()\n"
        ),

        "replacements": []
    },

    # =====================================================
    # ANALYST AGENT
    # =====================================================

    "core/agents/analyst_agent.py": {

        "append": "",

        "replacements": [

            (
                "from core.services.atr_service import (\n"
                "    AtrService\n"
                ")",

                "from core.services.atr_service import (\n"
                "    atr_service\n"
                ")"
            ),

            (
                "from core.services.market_structure_service import (\n"
                "    MarketStructureService\n"
                ")",

                "from core.services.market_structure_service import (\n"
                "    market_structure_service\n"
                ")"
            ),

            (
                "self.market_structure = (\n"
                "            MarketStructureService()\n"
                "        )",

                "self.market_structure = (\n"
                "            market_structure_service\n"
                "        )"
            ),

            (
                "self.atr_service = (\n"
                "            AtrService()\n"
                "        )",

                "self.atr_service = (\n"
                "            atr_service\n"
                "        )"
            )
        ]
    },

    # =====================================================
    # STRATEGY AGENT
    # =====================================================

    "core/agents/strategy_agent.py": {

        "append": "",

        "replacements": [

            (
                "from core.services.market_structure_service import (\n"
                "    MarketStructureService\n"
                ")",

                "from core.services.market_structure_service import (\n"
                "    market_structure_service\n"
                ")"
            ),

            (
                "self.market_structure = (\n"
                "            MarketStructureService()\n"
                "        )",

                "self.market_structure = (\n"
                "            market_structure_service\n"
                "        )"
            )
        ]
    },

    # =====================================================
    # SIGNAL QUALITY SERVICE
    # =====================================================

    "core/services/signal_quality_service.py": {

        "append": "",

        "replacements": [

            (
                "from core.services.ema_trend_service import (\n"
                "    EmaTrendService\n"
                ")",

                "from core.services.ema_trend_service import (\n"
                "    ema_trend_service\n"
                ")"
            ),

            (
                "from core.services.atr_service import (\n"
                "    AtrService\n"
                ")",

                "from core.services.atr_service import (\n"
                "    atr_service\n"
                ")"
            ),

            (
                "self.trend_service = (\n"
                "            EmaTrendService()\n"
                "        )",

                "self.trend_service = (\n"
                "            ema_trend_service\n"
                "        )"
            ),

            (
                "self.atr_service = (\n"
                "            AtrService()\n"
                "        )",

                "self.atr_service = (\n"
                "            atr_service\n"
                "        )"
            )
        ]
    }
}


def process_file(path, config):

    file_path = Path(path)

    if not file_path.exists():

        print(f"[ERROR] Missing: {path}")

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
                f"[OK] Replaced in {path}"
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
                f"[OK] Appended singleton in {path}"
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
        " FIX SHARED SERVICES"
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
        "[OK] SHARED SERVICES READY"
    )

    print(
        "=" * 60
    )

    print()


if __name__ == "__main__":

    main()