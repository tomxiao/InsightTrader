from __future__ import annotations

import json
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

    def get_by_task_id(self, task_id: str) -> dict | None:
        return self.task_doc


class FakeStateMachine:
    def __init__(self):
        self.transitions: list[dict] = []

    def transition(self, *, conversation_id: str, user_id: str, to_status: str) -> None:
        self.transitions.append(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "to_status": to_status,
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
    log_path = tmp_path / "logs" / "tom" / "insight_reply.jsonl"
    assert log_path.exists()

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["conversation_title"] == "SNDK 追问"
    assert record["conversation_id"] == "conv-1"
    assert record["reply_id"]
    assert record["reply_trace_dir"].endswith(record["reply_id"])
    assert record["report_dir"].endswith(str(Path("reports") / "SNDK_2026_0415_0820"))
    assert record["user_input"] == "主要风险是什么？"
    assert record["gating"]["intent"] == "risk"
    assert record["gating"]["primary_section"] == "risk_cons"
    assert record["gating"]["fallback_sections"] == ["research_mgr"]
    assert record["llm_router_ms"] == 123.4
    assert record["llm_reply_ms"] == 567.8
    assert "e2e_ms" not in record
    assert record["reply"] == "主要风险还是估值太高，回撤会被放大。"


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
