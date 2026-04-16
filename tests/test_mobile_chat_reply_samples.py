from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation.insight_reply.mobile_chat_reply_samples import evaluate_samples


def test_mobile_chat_reply_samples_harness_runs() -> None:
    rows = evaluate_samples()

    assert len(rows) == 5

    for row in rows:
        assert isinstance(row["final_answer"], str)
        assert row["final_answer"]
        assert row["char_count"] == len(row["final_answer"])
