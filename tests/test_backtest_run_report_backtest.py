from __future__ import annotations

from pathlib import Path

from backtest.run_report_backtest import _infer_batch_output_dir, _resolve_output_dir


def test_infer_batch_output_dir_uses_parent_of_reports(tmp_path: Path) -> None:
    report = tmp_path / "0419-2234-AXTI" / "reports" / "2026-0413-AXTI" / "2_decision" / "summary.md"
    report.parent.mkdir(parents=True)
    report.write_text("ok", encoding="utf-8")

    inferred = _infer_batch_output_dir([str(report)])

    assert inferred == (tmp_path / "0419-2234-AXTI").resolve()


def test_resolve_output_dir_prefers_inferred_batch_root(tmp_path: Path) -> None:
    report = tmp_path / "0419-2234-AXTI" / "reports" / "2026-0413-AXTI" / "2_decision" / "summary.md"
    report.parent.mkdir(parents=True)
    report.write_text("ok", encoding="utf-8")

    resolved = _resolve_output_dir([str(report)], None, "AXTI")

    assert resolved == (tmp_path / "0419-2234-AXTI").resolve()


def test_resolve_output_dir_uses_explicit_output_dir(tmp_path: Path) -> None:
    report = tmp_path / "0419-2234-AXTI" / "reports" / "2026-0413-AXTI" / "2_decision" / "summary.md"
    report.parent.mkdir(parents=True)
    report.write_text("ok", encoding="utf-8")
    explicit_output_dir = tmp_path / "custom-output"

    resolved = _resolve_output_dir([str(report)], str(explicit_output_dir), "AXTI")

    assert resolved == explicit_output_dir
