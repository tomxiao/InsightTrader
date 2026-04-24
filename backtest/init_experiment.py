from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tradingagents.agents.managers.decision_manager import build_decision_manager_prompt


def _default_experiment_name() -> str:
    return datetime.now().strftime("%Y-%m%d-round01")


def _write_decision_manager_prompt_snapshot(experiment_dir: Path) -> None:
    prompt_snapshot = build_decision_manager_prompt(
        instrument="{{instrument}}",
        trade_date="{{trade_date}}",
        market_report="{{market_report}}",
        news_report="{{news_report}}",
        fundamentals_report="{{fundamentals_report}}",
    )
    snapshot_lines = [
        "# Decision Manager Prompt Snapshot",
        "",
        "这个文件记录当前 round 初始化时的 `decision manager` prompt 模板。",
        "其中动态字段使用占位符保留，便于后续复盘 prompt 版本与 round 结果的对应关系。",
        "",
        "## Source",
        "",
        "- file: `tradingagents/agents/managers/decision_manager.py`",
        f"- captured_at: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## Prompt",
        "",
        "```text",
        prompt_snapshot,
        "```",
        "",
    ]
    (experiment_dir / "decision_manager_prompt_snapshot.md").write_text(
        "\n".join(snapshot_lines),
        encoding="utf-8",
    )


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
    parser.add_argument(
        "--mode",
        choices=["full_round", "decision_only_round"],
        default="full_round",
        help="Experiment mode. full_round builds a baseline; decision_only_round reuses analyst reports.",
    )
    parser.add_argument(
        "--baseline-round",
        help="Optional baseline experiment name or round id when mode=decision_only_round.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tickers = [item.strip() for item in args.tickers.split(",") if item.strip()]
    if not tickers:
        raise ValueError("At least one ticker is required.")

    experiment_dir = Path(args.base_dir) / args.name
    tickers_dir = experiment_dir / "tickers"
    reports_dir = experiment_dir / "reports"
    tickers_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    experiment_meta = {
        "name": args.name,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "sample_mode": args.sample_mode,
        "step": args.step,
        "tickers": tickers,
        "mode": args.mode,
        "baseline_round": args.baseline_round,
    }
    (experiment_dir / "experiment_meta.json").write_text(
        json.dumps(experiment_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_decision_manager_prompt_snapshot(experiment_dir)

    compare_stub = [
        f"# {args.name}",
        "",
        "## 本轮目标",
        "",
        "- 在这里填写本轮调优目标。",
        "",
        "## 跨标的总结",
        "",
        "- 在完成回测与信号标注后填写。",
        "",
    ]
    (experiment_dir / "compare.md").write_text("\n".join(compare_stub), encoding="utf-8")

    notes_stub = "\n".join(
        [
            "## 本轮目标",
            "",
            "- 在这里填写该标的本轮重点。",
            "",
            "## 改动内容",
            "",
            "- 在这里填写本轮运行前做了哪些调整。",
            "",
            "## 观察结论",
            "",
            "- 在这里填写复盘后的主要发现。",
            "",
            "## 下一步",
            "",
            "- 在这里填写下一步动作。",
            "",
        ]
    )
    for ticker in tickers:
        ticker_dir = tickers_dir / ticker
        (reports_dir / ticker).mkdir(parents=True, exist_ok=True)
        (ticker_dir / "batch").mkdir(parents=True, exist_ok=True)
        (ticker_dir / "result").mkdir(parents=True, exist_ok=True)
        (ticker_dir / "notes.md").write_text(notes_stub, encoding="utf-8")

    print(experiment_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
