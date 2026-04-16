from __future__ import annotations

from ta_service.workers.analysis_worker import _finalize_failed_stage_snapshot


def test_finalize_failed_stage_snapshot_marks_failed_stage_and_clears_other_in_progress() -> None:
    snapshot = _finalize_failed_stage_snapshot(
        {
            "analysts.market": "in_progress",
            "analysts.news": "in_progress",
            "analysts.fundamentals": "completed",
            "decision.finalize": "pending",
        },
        "analysts.market",
    )

    assert snapshot == {
        "analysts.market": "failed",
        "analysts.news": "pending",
        "analysts.fundamentals": "completed",
        "decision.finalize": "pending",
    }


def test_finalize_failed_stage_snapshot_adds_missing_failed_stage() -> None:
    snapshot = _finalize_failed_stage_snapshot({}, "analysts.market")

    assert snapshot == {"analysts.market": "failed"}
