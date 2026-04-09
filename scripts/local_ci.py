from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIX_LINT_RULES = "E4,E7,E9,F,I"


def run_step(name: str, command: list[str]) -> None:
    print(f"\n==> {name}")
    print(" ".join(command))
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_commands(fix: bool) -> list[tuple[str, list[str]]]:
    python = sys.executable
    commands: list[tuple[str, list[str]]] = []

    if fix:
        commands.append(("Format Python files", [python, "-m", "ruff", "format", "."]))
        commands.append(
            (
                "Auto-fix Python lint issues",
                [python, "-m", "ruff", "check", "--fix", "--select", FIX_LINT_RULES, "."],
            )
        )
    commands.append(("Check Python lint", [python, "-m", "ruff", "check", "."]))

    commands.append(
        ("Run unit tests", [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
    )
    commands.append(("Build package", [python, "-m", "build"]))
    return commands


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local TradingAgents lint, test, and build checks in a fixed order."
    )
    parser.add_argument(
        "--fix",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-fix formatting and lint issues before running tests and build (default: enabled).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    for name, command in build_commands(fix=args.fix):
        run_step(name, command)

    print("\nLocal CI completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
