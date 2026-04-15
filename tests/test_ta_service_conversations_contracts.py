from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.contracts.conversations import build_conversation_detail, build_task_progress


def _task_doc(**overrides: object) -> dict:
    document = {
        "taskId": "task-1",
        "status": "running",
        "stageId": "analysts.news",
        "nodeId": "News Analyst",
        "currentStep": None,
        "message": None,
        "elapsedTime": 12,
        "remainingTime": 408,
        "createdAt": "2026-04-15T10:00:00+00:00",
        "updatedAt": "2099-04-15T10:00:12+00:00",
    }
    document.update(overrides)
    return document


def test_build_task_progress_prefers_node_mapping_and_enriches_fields() -> None:
    progress = build_task_progress(_task_doc())

    assert progress.stageId == "analysts.news"
    assert progress.nodeId == "News Analyst"
    assert progress.displayState == "active"
    assert progress.currentStep == "新闻分析师整理近期关键事件"
    assert progress.message == "新闻分析师整理近期关键事件"


def test_build_conversation_detail_keeps_task_progress_for_report_ready() -> None:
    conversation = {
        "id": "conv-1",
        "title": "TSLA",
        "status": "report_ready",
        "updatedAt": "2026-04-15T10:10:00+00:00",
    }
    messages = [
        {
            "id": "msg-1",
            "role": "assistant",
            "messageType": "summary_card",
            "content": {"text": "summary"},
            "createdAt": "2026-04-15T10:10:00+00:00",
        }
    ]

    detail = build_conversation_detail(conversation, messages, _task_doc(status="completed"))

    assert detail.taskProgress is not None
    assert detail.taskProgress.displayState == "done"


def test_build_conversation_detail_keeps_task_progress_for_failed_conversation() -> None:
    conversation = {
        "id": "conv-1",
        "title": "TSLA",
        "status": "failed",
        "updatedAt": "2026-04-15T10:10:00+00:00",
    }

    detail = build_conversation_detail(conversation, [], _task_doc(status="failed", updatedAt="2026-04-15T10:10:00+00:00"))

    assert detail.taskProgress is not None
    assert detail.taskProgress.displayState == "failed"
