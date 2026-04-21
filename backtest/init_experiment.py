from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _default_experiment_name() -> str:
    return datetime.now().strftime("%Y-%m%d-round01")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a scaffold for a multi-ticker backtest tuning experiment.")
    parser.add_argument(
        "--name",
        default=_default_experiment_name(),
        help="Experiment directory name. Defaults to YYYY-MMdd-round01.",
    )
    parser.add_argument(
        "--tickers",
        required=True,
        help="Comma-separated tickers, e.g. AXTI,1347.HK",
    )
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD.")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD.")
    parser.add_argument(
        "--sample-mode",
        choices=["daily", "weekly"],
        default="daily",
        help="Sampling frequency shared by this experiment.",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=1,
        help="Step used only for daily sampling.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path("backtest") / "experiments"),
        help="Base directory for experiment scaffolds.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tickers = [item.strip() for item in args.tickers.split(",") if item.strip()]
    if not tickers:
        raise ValueError("At least one ticker is required.")

    experiment_dir = Path(args.base_dir) / args.name
    tickers_dir = experiment_dir / "tickers"
    tickers_dir.mkdir(parents=True, exist_ok=True)

    experiment_meta = {
        "name": args.name,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "sample_mode": args.sample_mode,
        "step": args.step,
        "tickers": tickers,
    }
    (experiment_dir / "experiment_meta.json").write_text(
        json.dumps(experiment_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    compare_stub = [
        f"# {args.name}",
        "",
        "## Goal",
        "",
        "- Fill in the tuning goal for this round.",
        "",
        "## Cross-Ticker Summary",
        "",
        "- Fill in after running backtests and labels.",
        "",
    ]
    (experiment_dir / "compare.md").write_text("\n".join(compare_stub), encoding="utf-8")

    notes_stub = "\n".join(
        [
            "## Goal",
            "",
            "- Fill in the ticker-specific focus for this round.",
            "",
            "## Changes",
            "",
            "- Fill in what changed before this run.",
            "",
            "## Findings",
            "",
            "- Fill in the main observations after review.",
            "",
            "## Next Step",
            "",
            "- Fill in the next action.",
            "",
        ]
    )
    for ticker in tickers:
        ticker_dir = tickers_dir / ticker
        (ticker_dir / "batch").mkdir(parents=True, exist_ok=True)
        (ticker_dir / "result").mkdir(parents=True, exist_ok=True)
        (ticker_dir / "notes.md").write_text(notes_stub, encoding="utf-8")

    print(experiment_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
