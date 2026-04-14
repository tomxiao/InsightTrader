import unittest
from types import SimpleNamespace

from ta_service.models.message_types import MessageType
from ta_service.models.report_insight import ReportInsightContext, ReportInsightResult
from ta_service.services.conversation_service import ConversationService


class FakeConversationRepo:
    def __init__(self, conversation):
        self.conversation = conversation

    def get_for_user(self, *, conversation_id: str, user_id: str):
        if self.conversation["id"] == conversation_id and self.conversation["userId"] == user_id:
            return self.conversation
        return None


class FakeMessageRepo:
    def __init__(self, messages=None):
        self.created = []
        self._messages = messages or []

    def create(self, *, conversation_id: str, role: str, content, message_type: str = "text"):
        document = {
            "id": f"message-{len(self.created) + 1}",
            "conversationId": conversation_id,
            "role": role,
            "messageType": message_type,
            "content": content,
            "createdAt": "2026-04-09T12:00:00+00:00",
        }
        self.created.append(document)
        return document

    def list_for_conversation(self, conversation_id: str):
        return self._messages


class FakeTaskRepo:
    def __init__(self, task_doc=None):
        self._task_doc = task_doc

    def get_active_for_user(self, user_id: str, ttl_seconds: int = 7200):
        return None

    def get_by_task_id(self, task_id: str):
        return self._task_doc


class FakeStateMachine:
    def transition(self, **kwargs):
        pass


class FakeReportContextLoader:
    def __init__(self, sections=None):
        self._sections = sections or {}

    def load(self, *, trace_dir):
        return self._sections


class FakeReportInsightAgent:
    def __init__(self, answer_text: str, is_answerable: bool = True):
        self._answer = answer_text
        self._is_answerable = is_answerable

    def answer(self, *, context: ReportInsightContext) -> ReportInsightResult:
        return ReportInsightResult(
            answer=self._answer,
            is_answerable=self._is_answerable,
        )


def _build_service(
    conversation,
    messages=None,
    task_doc=None,
    report_sections=None,
    agent_answer="这是一个测试回答",
    agent_is_answerable=True,
):
    return ConversationService(
        conversation_repo=FakeConversationRepo(conversation),
        message_repo=FakeMessageRepo(messages or []),
        task_repo=FakeTaskRepo(task_doc=task_doc),
        state_machine=FakeStateMachine(),
        settings=SimpleNamespace(
            analysis_task_ttl_seconds=7200,
            followup_history_turns=6,
        ),
        report_context_loader=FakeReportContextLoader(sections=report_sections),
        report_insight_agent=FakeReportInsightAgent(
            answer_text=agent_answer,
            is_answerable=agent_is_answerable,
        ),
    )


class ConversationServiceTests(unittest.TestCase):
    def test_post_message_without_summary_returns_no_context_reply(self):
        """无 SUMMARY_CARD 且无报告文件时，Agent 返回无上下文提示。"""
        conversation = {
            "id": "conv-1",
            "userId": "user-1",
            "status": "report_ready",
        }
        service = _build_service(
            conversation,
            agent_answer="当前会话暂无可用的分析报告内容，无法回答该问题。",
            agent_is_answerable=False,
        )

        response = service.post_message(
            user_id="user-1",
            conversation_id="conv-1",
            message="主要风险是什么？",
        )

        self.assertEqual(len(response.messages), 2)
        self.assertIn("当前会话暂无可用的分析报告内容", response.messages[-1].content)

    def test_post_message_uses_report_sections_when_available(self):
        """有报告章节时，Agent 能正常被调用并返回回答。"""
        conversation = {
            "id": "conv-2",
            "userId": "user-1",
            "status": "report_ready",
            "currentTaskId": "task-1",
        }
        task_doc = {
            "taskId": "task-1",
            "symbol": "AAPL",
            "tradeDate": "2026-04-14",
            "traceDir": "D:/CodeBase/InsightTrader/results/ta_service/AAPL/2026-04-14/run_1",
        }
        sections = {
            "decision": "建议买入，目标价 $200。",
            "fundamentals": "基本面稳健，PE 合理。",
        }
        service = _build_service(
            conversation,
            task_doc=task_doc,
            report_sections=sections,
            agent_answer="根据分析报告，主要风险在于宏观环境不确定性。",
        )

        response = service.post_message(
            user_id="user-1",
            conversation_id="conv-2",
            message="主要风险是什么？",
        )

        self.assertEqual(len(response.messages), 2)
        self.assertIn("主要风险在于宏观环境不确定性", response.messages[-1].content)

    def test_post_message_falls_back_to_summary_when_no_report_files(self):
        """traceDir 存在但报告文件不可用时，降级到 SUMMARY_CARD 文本。"""
        conversation = {
            "id": "conv-3",
            "userId": "user-1",
            "status": "report_ready",
            "currentTaskId": "task-2",
        }
        task_doc = {
            "taskId": "task-2",
            "symbol": "TSLA",
            "tradeDate": "2026-04-14",
            "traceDir": "D:/nonexistent/path",
        }
        summary_message = {
            "id": "msg-1",
            "conversationId": "conv-3",
            "role": "assistant",
            "messageType": MessageType.SUMMARY_CARD,
            "content": {"text": "报告认为核心风险在于估值偏高和短期波动。"},
            "createdAt": "2026-04-09T12:00:00+00:00",
        }
        # FakeReportContextLoader returns empty dict (simulating no files on disk)
        service = _build_service(
            conversation,
            messages=[summary_message],
            task_doc=task_doc,
            report_sections={},  # loader returns empty
            agent_answer="基于摘要：核心风险在于估值偏高。",
        )

        response = service.post_message(
            user_id="user-1",
            conversation_id="conv-3",
            message="主要风险是什么？",
        )

        self.assertEqual(len(response.messages), 2)
        self.assertIn("核心风险在于估值偏高", response.messages[-1].content)

    def test_post_message_includes_conversation_history(self):
        """历史消息中的 TEXT 消息应被传入 Agent context。"""
        conversation = {
            "id": "conv-4",
            "userId": "user-1",
            "status": "report_explaining",
            "currentTaskId": "task-3",
        }
        task_doc = {
            "taskId": "task-3",
            "symbol": "MSFT",
            "tradeDate": "2026-04-14",
            "traceDir": None,
        }
        prior_messages = [
            {
                "id": "msg-1",
                "role": "user",
                "messageType": MessageType.TEXT,
                "content": "估值如何？",
                "createdAt": "2026-04-09T12:00:00+00:00",
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "messageType": MessageType.INSIGHT_REPLY,
                "content": "PE 约 30 倍，合理。",
                "createdAt": "2026-04-09T12:01:00+00:00",
            },
        ]

        captured_contexts = []

        class CapturingAgent:
            def answer(inner_self, *, context: ReportInsightContext) -> ReportInsightResult:
                captured_contexts.append(context)
                return ReportInsightResult(answer="回答", is_answerable=True)

        service = ConversationService(
            conversation_repo=FakeConversationRepo(conversation),
            message_repo=FakeMessageRepo(prior_messages),
            task_repo=FakeTaskRepo(task_doc=task_doc),
            state_machine=FakeStateMachine(),
            settings=SimpleNamespace(
                analysis_task_ttl_seconds=7200,
                followup_history_turns=6,
            ),
            report_context_loader=FakeReportContextLoader(),
            report_insight_agent=CapturingAgent(),
        )

        service.post_message(
            user_id="user-1",
            conversation_id="conv-4",
            message="短期如何看？",
        )

        self.assertEqual(len(captured_contexts), 1)
        ctx = captured_contexts[0]
        self.assertEqual(ctx.question, "短期如何看？")
        # history should include the 2 prior TEXT messages
        self.assertEqual(len(ctx.conversation_history), 2)
        self.assertEqual(ctx.conversation_history[0]["role"], "user")
        self.assertEqual(ctx.conversation_history[1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
