from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.models.message_types import MessageType
from ta_service.models.report_insight import ReportInsightResult
from ta_service.services.conversation_service import ConversationService


class FakeConversationRepo:
    def __init__(self, conversation: dict):
        self.conversation = conversation

    def get_for_user(self, *, conversation_id: str, user_id: str) -> dict | None:
        if conversation_id == self.conversation["id"] and user_id == self.conversation["userId"]:
            return dict(self.conversation)
        return None


class FakeMessageRepo:
    def __init__(self, messages: list[dict] | None = None):
        self.messages = list(messages or [])
        self.created: list[dict] = []

    def list_for_conversation(self, conversation_id: str) -> list[dict]:
        return list(self.messages)

    def create(self, *, conversation_id: str, role: str, message_type: MessageType, content):
        document = {
            "id": f"msg-{len(self.created) + 1}",
            "conversationId": conversation_id,
            "role": role,
            "messageType": message_type,
            "content": content,
            "createdAt": "2026-04-16T00:00:00+00:00",
        }
        self.created.append(document)
        self.messages.append(document)
        return document


class FakeTaskRepo:
    def __init__(self, task_doc: dict | None):
        self.task_doc = task_doc
        self.updated_statuses: list[dict] = []

    def get_by_task_id(self, task_id: str) -> dict | None:
        return self.task_doc

    def update_status(self, task_id: str, **fields) -> None:
        self.updated_statuses.append({"task_id": task_id, **fields})
        if self.task_doc and self.task_doc.get("taskId") == task_id:
            self.task_doc.update(fields)


class FakeStateMachine:
    def __init__(self):
        self.transitions: list[dict] = []

    def transition(
        self,
        *,
        conversation_id: str,
        user_id: str,
        to_status: str,
        task_id=None,
    ) -> None:
        self.transitions.append(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "to_status": to_status,
                "task_id": task_id,
            }
        )


class FakeReportContextLoader:
    def list_available_sections(self, *, trace_dir: str, team_id: str | None = None) -> list[str]:
        return ["decision", "risk_cons"]


class FakeReportInsightAgent:
    def answer(self, *, context):
        return ReportInsightResult(
            answer="主要风险还是估值太高，回撤会被放大。",
            is_answerable=True,
            source_sections=["executive_summary", "risk_cons"],
            routing_intent="risk",
            routing_primary_section="risk_cons",
            routing_fallback_sections=["research_mgr"],
            routing_reason="matched risk keyword",
            llm_router_ms=123.4,
            llm_reply_ms=567.8,
        )


def test_post_message_writes_user_scoped_insight_reply_log(tmp_path: Path) -> None:
    conversation = {
        "id": "conv-1",
        "userId": "user-1",
        "title": "SNDK 追问",
        "status": "report_ready",
        "currentTaskId": "task-1",
    }
    task_doc = {
        "traceDir": str(tmp_path / "results" / "analysis" / "SNDK_2026_0415_0820"),
        "symbol": "SNDK",
        "tradeDate": "2026-04-15",
    }
    service = ConversationService(
        conversation_repo=FakeConversationRepo(conversation),
        message_repo=FakeMessageRepo(
            [
                {
                    "id": "sum-1",
                    "conversationId": "conv-1",
                    "role": "assistant",
                    "messageType": MessageType.SUMMARY_CARD,
                    "content": {"text": "执行摘要：偏谨慎，主要因为估值太高。"},
                    "createdAt": "2026-04-16T00:00:00+00:00",
                }
            ]
        ),
        task_repo=FakeTaskRepo(task_doc),
        state_machine=FakeStateMachine(),
        settings=SimpleNamespace(
            analysis_task_ttl_seconds=7200,
            followup_history_turns=6,
            results_root=tmp_path / "results" / "analysis",
            logs_root=tmp_path / "logs",
            reports_root=tmp_path / "reports",
        ),
        report_context_loader=FakeReportContextLoader(),
        report_insight_agent=FakeReportInsightAgent(),
    )

    response = service.post_message(
        user_id="user-1",
        username="tom",
        conversation_id="conv-1",
        message="主要风险是什么？",
    )

    assert len(response.messages) == 2
    log_path = tmp_path / "logs" / "user" / "tom.jsonl"
    assert log_path.exists()

    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 2

    user_record, assistant_record = records
    assert user_record["conversationId"] == "conv-1"
    assert user_record["userName"] == "tom"
    assert user_record["phase"] == "insight_reply"
    assert user_record["event"] == "user_input"
    assert user_record["message"] == "主要风险是什么？"

    assert assistant_record["conversationId"] == "conv-1"
    assert assistant_record["userName"] == "tom"
    assert assistant_record["phase"] == "insight_reply"
    assert assistant_record["event"] == "assistant_reply"
    assert assistant_record["replyId"]
    assert assistant_record["routingIntent"] == "risk"
    assert assistant_record["routingPrimarySection"] == "risk_cons"
    assert assistant_record["routingFallbackSections"] == ["research_mgr"]
    assert assistant_record["llmRouterMs"] == 123.4
    assert assistant_record["llmReplyMs"] == 567.8
    assert assistant_record["reply"] == "主要风险还是估值太高，回撤会被放大。"


def test_build_conversation_history_keeps_only_recent_two_rounds(tmp_path: Path) -> None:
    service = ConversationService(
        conversation_repo=FakeConversationRepo(
            {
                "id": "conv-1",
                "userId": "user-1",
                "title": "SNDK 追问",
                "status": "report_explaining",
                "currentTaskId": "task-1",
            }
        ),
        message_repo=FakeMessageRepo(),
        task_repo=FakeTaskRepo(None),
        state_machine=FakeStateMachine(),
        settings=SimpleNamespace(
            analysis_task_ttl_seconds=7200,
            followup_history_turns=6,
            results_root=tmp_path / "results" / "analysis",
            logs_root=tmp_path / "logs",
            reports_root=tmp_path / "reports",
        ),
        report_context_loader=FakeReportContextLoader(),
        report_insight_agent=FakeReportInsightAgent(),
    )

    history = service._build_conversation_history(
        all_messages=[
            {"role": "user", "messageType": MessageType.TEXT, "content": "u1"},
            {"role": "assistant", "messageType": MessageType.INSIGHT_REPLY, "content": "a1"},
            {"role": "user", "messageType": MessageType.TEXT, "content": "u2"},
            {"role": "assistant", "messageType": MessageType.INSIGHT_REPLY, "content": "a2"},
            {"role": "user", "messageType": MessageType.TEXT, "content": "u3"},
            {"role": "assistant", "messageType": MessageType.INSIGHT_REPLY, "content": "a3"},
        ]
    )

    assert history == [
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
        {"role": "assistant", "content": "a3"},
    ]


def test_append_user_trace_falls_back_to_unknown_when_username_missing(tmp_path: Path) -> None:
    from ta_service.runtime.user_trace import append_user_trace

    append_user_trace(
        user_id="",
        username=None,
        conversation_id="conv-unknown",
        phase="resolution",
        event="user_input",
        settings=SimpleNamespace(logs_root=tmp_path / "logs"),
        message="hello",
    )

    log_path = tmp_path / "logs" / "user" / "unknown.jsonl"
    assert log_path.exists()

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["userName"] == "unknown"
    assert record["conversationId"] == "conv-unknown"
    assert record["phase"] == "resolution"
    assert record["event"] == "user_input"


def test_get_conversation_reconciles_timed_out_analysis_to_failed(tmp_path: Path) -> None:
    conversation = {
        "id": "conv-timeout",
        "userId": "user-1",
        "title": "中国平安",
        "status": "analyzing",
        "currentTaskId": "task-timeout",
        "updatedAt": "2026-04-16T00:00:00+00:00",
    }
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    task_repo = FakeTaskRepo(
        {
            "taskId": "task-timeout",
            "status": "running",
            "stageId": "analysts.market",
            "nodeId": "Market Analyst",
            "currentStep": "分析中",
            "message": "分析中",
            "elapsedTime": 120,
            "remainingTime": 300,
            "stageSnapshot": {},
            "stageTimeline": {},
            "createdAt": stale_time,
            "updatedAt": stale_time,
        }
    )
    message_repo = FakeMessageRepo()
    state_machine = FakeStateMachine()
    service = ConversationService(
        conversation_repo=FakeConversationRepo(conversation),
        message_repo=message_repo,
        task_repo=task_repo,
        state_machine=state_machine,
        settings=SimpleNamespace(
            analysis_task_ttl_seconds=180,
            followup_history_turns=6,
            results_root=tmp_path / "results" / "analysis",
            logs_root=tmp_path / "logs",
            reports_root=tmp_path / "reports",
        ),
        report_context_loader=FakeReportContextLoader(),
        report_insight_agent=FakeReportInsightAgent(),
    )

    detail = service.get_conversation(user_id="user-1", conversation_id="conv-timeout")

    assert detail is not None
    assert detail.status == "failed"
    assert detail.taskProgress is not None
    assert detail.taskProgress.status == "failed"
    assert task_repo.updated_statuses[-1]["status"] == "failed"
    assert state_machine.transitions[-1]["to_status"] == "failed"
    assert message_repo.created[-1]["messageType"] == MessageType.ERROR
