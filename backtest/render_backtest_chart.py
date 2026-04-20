from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
import pandas as pd
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _pick_cjk_font() -> None:
    candidates = [
        "Microsoft YaHei",
        "Microsoft JhengHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "PingFang SC",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def _fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):.1f}%"


def _perf_color(value: float | int | None, default: str) -> str:
    if value is None:
        return default
    value = float(value)
    if value > 0:
        return "#e05260"
    if value < 0:
        return "#2f9e5f"
    return default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a backtest result chart.")
    parser.add_argument("--output-dir", required=True, help="Directory containing signals.csv/trades.csv/summary.json.")
    parser.add_argument("--ohlcv-csv", help="Optional OHLCV CSV override. Defaults to the local *-ohlcv.csv in output-dir.")
    parser.add_argument("--out", help="Optional target PNG path.")
    return parser


def _resolve_local_ohlcv_csv(output_dir: Path, ohlcv_csv: Path | None) -> Path:
    if ohlcv_csv is not None:
        return ohlcv_csv

    preferred = output_dir / f"{output_dir.name}-ohlcv.csv"
    if preferred.exists():
        return preferred

    matches = sorted(output_dir.glob("*-ohlcv.csv"))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        f"No local OHLCV CSV found under {output_dir}. Expected {preferred.name} or another *-ohlcv.csv file."
    )


def render_chart(output_dir: Path, ohlcv_csv: Path | None = None, out_path: Path | None = None) -> Path:
    _pick_cjk_font()

    ohlcv_csv = _resolve_local_ohlcv_csv(output_dir, ohlcv_csv)
    ohlcv = pd.read_csv(ohlcv_csv)
    ohlcv["Date"] = pd.to_datetime(ohlcv["Date"])

    with (output_dir / "signals.csv").open(encoding="utf-8-sig") as handle:
        signals = list(csv.DictReader(handle))
    with (output_dir / "trades.csv").open(encoding="utf-8-sig") as handle:
        trades = list(csv.DictReader(handle))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    if out_path is None:
        out_path = output_dir / f"{output_dir.name}-bt.png"

    x_map = {date: idx for idx, date in enumerate(ohlcv["Date"])}

    fig = plt.figure(figsize=(15, 9), dpi=180, facecolor="#0f1115")
    gs = fig.add_gridspec(
        3,
        4,
        height_ratios=[0.55, 3.5, 1.0],
        width_ratios=[1, 1, 1, 1.0],
        hspace=0.08,
        wspace=0.14,
    )
    ax_title = fig.add_subplot(gs[0, :3])
    ax_perf = fig.add_subplot(gs[:, 3])
    ax = fig.add_subplot(gs[1, :3])
    ax_pos = fig.add_subplot(gs[2, :3], sharex=ax)
    for axis in (ax_title, ax_perf):
        axis.axis("off")

    ax_title.set_xlim(0, 1)
    ax_title.set_ylim(0, 1)
    ax_title.text(0.0, 0.74, "AXTI 回测信号复盘", fontsize=22, fontweight="bold", color="#f3f5f7")
    ax_title.text(
        0.0,
        0.34,
        f"批次 {output_dir.name}   {ohlcv['Date'].min():%Y-%m-%d} ~ {ohlcv['Date'].max():%Y-%m-%d}   日频",
        fontsize=11.5,
        color="#a9b1ba",
    )
    ax_title.text(
        0.0,
        0.03,
        "红涨绿跌；蓝/红三角为信号日，亮绿色三角为实际成交，X 为实际退出。",
        fontsize=10,
        color="#7f8791",
    )

    panel_bg = "#151922"
    grid = "#2a3240"
    axis_c = "#3a4454"
    text_dim = "#93a0b2"
    text_main = "#edf2f7"
    up_fill, up_edge = "#e05260", "#ff7b86"
    down_fill, down_edge = "#2f9e5f", "#59c184"

    ax.set_facecolor(panel_bg)
    width = 0.62
    for idx, row in ohlcv.iterrows():
        open_, high, low, close = row["Open"], row["High"], row["Low"], row["Close"]
        fill = up_fill if close >= open_ else down_fill
        edge = up_edge if close >= open_ else down_edge
        ax.vlines(idx, low, high, color=edge, linewidth=1.15, zorder=1)
        lower = min(open_, close)
        height = max(abs(close - open_), 0.18)
        ax.add_patch(
            Rectangle(
                (idx - width / 2, lower),
                width,
                height,
                facecolor=fill,
                edgecolor=edge,
                linewidth=0.8,
                zorder=2,
            )
        )

    for row in signals:
        signal_date = pd.to_datetime(row["trade_date"])
        if signal_date not in x_map:
            continue
        x = x_map[signal_date]
        day = ohlcv.loc[ohlcv["Date"] == signal_date].iloc[0]
        if row["action"] == "buy_on_pullback":
            ax.scatter(x, day["Low"] - 1.1, marker="^", s=62, color=up_fill, zorder=4)
        elif row["action"] == "sell":
            ax.scatter(x, day["High"] + 1.1, marker="v", s=62, color=down_fill, zorder=4)

    position_delta = {date: 0 for date in ohlcv["Date"]}
    for row in trades:
        quantity = int(row.get("quantity") or 1)
        if row["entry_date"]:
            entry_date = pd.to_datetime(row["entry_date"])
            if entry_date in position_delta:
                position_delta[entry_date] += quantity
        if row["exit_date"] and row["action"].startswith("buy") and row["status"] == "triggered":
            exit_date = pd.to_datetime(row["exit_date"])
            if exit_date in position_delta:
                position_delta[exit_date] -= quantity

    positions: list[int] = []
    current = 0
    for date in ohlcv["Date"]:
        current += position_delta.get(date, 0)
        positions.append(current)

    for row in trades:
        if row["entry_date"]:
            entry_date = pd.to_datetime(row["entry_date"])
            if entry_date in x_map:
                ax.scatter(
                    x_map[entry_date],
                    float(row["entry_price"]),
                    marker="^",
                    s=92,
                    facecolor=up_fill,
                    edgecolor="#f3f5f7",
                    linewidth=1.2,
                    zorder=5,
                )
        if row["exit_date"] and row["action"].startswith("buy") and row["status"] == "triggered":
            exit_date = pd.to_datetime(row["exit_date"])
            if exit_date in x_map:
                ax.scatter(
                    x_map[exit_date],
                    float(row["exit_price"]),
                    marker="v",
                    s=82,
                    facecolor=down_fill,
                    edgecolor="#f3f5f7",
                    linewidth=1.2,
                    zorder=5,
                )

    for row in trades:
        if row["action"] == "buy_on_pullback" and row["entry_date"] and row["trade_date"] != row["entry_date"]:
            signal_date = pd.to_datetime(row["trade_date"])
            entry_date = pd.to_datetime(row["entry_date"])
            if signal_date in x_map and entry_date in x_map:
                ax.plot(
                    [x_map[signal_date], x_map[entry_date]],
                    [float(row["entry_price"]), float(row["entry_price"])],
                    linestyle=(0, (3, 2)),
                    color="#7f8b97",
                    linewidth=0.9,
                    zorder=3,
                )

    for row in trades:
        if row["action"] == "sell" and row["status"] == "triggered_exit" and row.get("trade_date") and row.get("exit_date"):
            signal_date = pd.to_datetime(row["trade_date"])
            exit_date = pd.to_datetime(row["exit_date"])
            if signal_date in x_map and exit_date in x_map and row.get("exit_price"):
                ax.plot(
                    [x_map[signal_date], x_map[exit_date]],
                    [float(row["exit_price"]), float(row["exit_price"])],
                    linestyle=(0, (3, 2)),
                    color="#7f8b97",
                    linewidth=0.9,
                    zorder=3,
                )

    ax.set_ylabel("价格（美元）", fontsize=11, color=text_main)
    ax.grid(axis="y", color=grid, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(axis_c)
    ax.tick_params(colors="#d7dde5", labelsize=10)
    ax.set_xlim(-0.8, len(ohlcv) - 0.2)
    plt.setp(ax.get_xticklabels(), visible=False)

    legend_items = [
        Line2D([0], [0], color=up_fill, lw=6, label="上涨K线"),
        Line2D([0], [0], color=down_fill, lw=6, label="下跌K线"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=up_fill, markeredgecolor=up_fill, markersize=8, label="买入信号"),
        Line2D([0], [0], marker="v", color="w", markerfacecolor=down_fill, markeredgecolor=down_fill, markersize=8, label="卖出信号"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=up_fill, markeredgecolor="#f3f5f7", markeredgewidth=1.2, markersize=8.5, label="实际买入"),
        Line2D([0], [0], marker="v", color="w", markerfacecolor=down_fill, markeredgecolor="#f3f5f7", markeredgewidth=1.2, markersize=8.5, label="实际卖出"),
    ]
    legend = ax.legend(handles=legend_items, loc="upper left", ncol=4, fontsize=8.6, frameon=False, borderaxespad=0.4)
    for text in legend.get_texts():
        text.set_color("#dce3ea")

    ax_pos.set_facecolor(panel_bg)
    ax_pos.step(range(len(ohlcv)), positions, where="mid", color="#86a3bd", linewidth=2.0)
    ax_pos.fill_between(range(len(ohlcv)), positions, step="mid", color="#30404f", alpha=0.95)
    ax_pos.set_ylabel("持仓股数", fontsize=10.5, color=text_main)
    ax_pos.set_xlabel("交易日期", fontsize=10.5, color=text_main)
    ax_pos.set_ylim(0, max(positions + [1]) + 0.35)
    ax_pos.set_yticks(sorted(set(positions + [0])))
    ax_pos.grid(axis="y", color=grid, linewidth=0.8)
    ax_pos.spines[["top", "right"]].set_visible(False)
    ax_pos.spines[["left", "bottom"]].set_color(axis_c)
    ax_pos.tick_params(colors="#d7dde5", labelsize=9.5)
    ax_pos.set_xticks(range(len(ohlcv)))
    ax_pos.set_xticklabels([date.strftime("%m-%d") for date in ohlcv["Date"]], rotation=45, ha="right", fontsize=9.5)

    ax_perf.set_xlim(0, 1)
    ax_perf.set_ylim(0, 1)
    ax_perf.add_patch(Rectangle((0, 0), 1, 1, facecolor="#12161d", edgecolor="#252c37", linewidth=1.2))
    ax_perf.text(0.08, 0.96, "绩效概览", fontsize=15, fontweight="bold", color=text_main, va="top")
    ax_perf.hlines([0.925], 0.08, 0.92, colors="#242d38", linewidth=1)

    stats = [
        ("信号总数", f"{summary['signal_count']}"),
        ("实际成交", f"{summary['trade_count']}"),
        ("胜率", _fmt_pct(summary["win_rate"])),
        ("平均收益", _fmt_pct(summary["avg_return"])),
        ("中位数收益", _fmt_pct(summary["median_return"])),
    ]
    y = 0.87
    for label, value in stats:
        ax_perf.text(0.08, y, label, fontsize=10, color=text_dim, va="top")
        raw_value = summary["avg_return"] if label == "平均收益" else summary["median_return"] if label == "中位数收益" else None
        value_color = _perf_color(raw_value, text_main) if label in {"平均收益", "中位数收益"} else text_main
        ax_perf.text(0.92, y, value, fontsize=14, fontweight="bold", color=value_color, ha="right", va="top")
        y -= 0.095

    ax_perf.text(0.08, 0.39, "单笔最佳", fontsize=10, color=text_dim, va="top")
    ax_perf.text(
        0.92,
        0.39,
        _fmt_pct(summary["max_return"]),
        fontsize=13,
        fontweight="bold",
        color=_perf_color(summary["max_return"], text_main),
        ha="right",
        va="top",
    )
    ax_perf.text(0.08, 0.33, "单笔最差", fontsize=10, color=text_dim, va="top")
    ax_perf.text(
        0.92,
        0.33,
        _fmt_pct(summary["min_return"]),
        fontsize=13,
        fontweight="bold",
        color=_perf_color(summary["min_return"], text_main),
        ha="right",
        va="top",
    )

    by_action = summary["by_action"]
    ax_perf.text(0.08, 0.24, "动作分布", fontsize=11, fontweight="bold", color=text_main)
    ax_perf.text(0.08, 0.20, f"择机买入  {by_action.get('buy_on_pullback', {}).get('signal_count')}", fontsize=10.5, color="#d8dee7")
    ax_perf.text(0.08, 0.16, f"保持观望  {by_action.get('hold', {}).get('signal_count')}", fontsize=10.5, color="#d8dee7")
    ax_perf.text(0.08, 0.12, f"建议卖出  {by_action.get('sell', {}).get('signal_count')}", fontsize=10.5, color="#d8dee7")

    fig.text(0.012, 0.012, "InsightTrader backtest visualized by Codex", fontsize=8.5, color="#6d7682")
    fig.savefig(out_path, bbox_inches="tight", facecolor="#0f1115")
    return out_path


def main() -> int:
    args = build_parser().parse_args()
    output_path = render_chart(
        Path(args.output_dir),
        Path(args.ohlcv_csv) if args.ohlcv_csv else None,
        Path(args.out) if args.out else None,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
