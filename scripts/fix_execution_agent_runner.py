# -*- coding: utf-8 -*-

from pathlib import Path


RUNNERS = [

    "apps/trader/runner.py",
    "backtest/runner.py"
]


IMPORT_BLOCK = (
    "from core.agents.execution_agent import (\n"
    "    ExecutionAgent\n"
    ")\n"
)


EXECUTION_INIT = (
    "    ExecutionAgent(bus)\n"
)


def add_import(content: str):

    if (
        "from core.agents.execution_agent import"
        in content
    ):

        return content

    marker = (
        "from core.agents.risk_agent import (\n"
        "    RiskAgent\n"
        ")\n"
    )

    if marker not in content:

        print(
            "[WARN] RiskAgent import marker not found"
        )

        return content

    return content.replace(
        marker,
        marker + "\n" + IMPORT_BLOCK
    )


def add_execution_agent(content: str):

    if "ExecutionAgent(bus)" in content:

        return content

    marker = (
        "    RiskAgent(bus)\n"
    )

    if marker not in content:

        print(
            "[WARN] RiskAgent init marker not found"
        )

        return content

    return content.replace(
        marker,
        marker + "\n" + EXECUTION_INIT
    )


def process_runner(path_str: str):

    path = Path(path_str)

    if not path.exists():

        print(
            f"[ERROR] Missing: {path}"
        )

        return

    content = path.read_text(
        encoding="utf-8"
    )

    original = content

    content = add_import(
        content
    )

    content = add_execution_agent(
        content
    )

    if content != original:

        path.write_text(
            content,
            encoding="utf-8"
        )

        print(
            f"[OK] Updated: {path}"
        )

    else:

        print(
            f"[SKIP] No changes: {path}"
        )


def main():

    print()

    print("=" * 60)

    print(" FIX EXECUTION AGENT RUNNER ")

    print("=" * 60)

    print()

    for runner in RUNNERS:

        process_runner(
            runner
        )

    print()

    print("=" * 60)

    print("[OK] EXECUTION AGENT READY")

    print("=" * 60)

    print()


if __name__ == "__main__":

    main()