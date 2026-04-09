import unittest

from ta_service.services.conversation_service import ConversationService


class FakeConversationRepo:
    def __init__(self, conversation):
        self.conversation = conversation
        self.updated = None

    def get_for_user(self, *, conversation_id: str, user_id: str):
        if self.conversation["id"] == conversation_id and self.conversation["userId"] == user_id:
            return self.conversation
        return None

    def update_metadata(self, *, conversation_id: str, user_id: str, title=None, status=None):
        self.updated = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": title,
            "status": status,
        }
        if status is not None:
            self.conversation["status"] = status


class FakeMessageRepo:
    def __init__(self):
        self.created = []

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
        return [item for item in self.created if item["conversationId"] == conversation_id]


class FakeReportRepo:
    def __init__(self, report=None):
        self.report = report

    def get_for_user(self, *, report_id: str, user_id: str):
        if self.report and self.report["id"] == report_id and self.report["userId"] == user_id:
            return self.report
        return None

    def get_latest_for_conversation(self, *, conversation_id: str, user_id: str):
        if self.report and self.report["conversationId"] == conversation_id and self.report["userId"] == user_id:
            return self.report
        return None


class ConversationServiceTests(unittest.TestCase):
    def test_post_message_without_report_returns_guidance_message(self):
        conversation = {
            "id": "conv-1",
            "userId": "user-1",
            "status": "idle",
            "lastReportId": None,
        }
        service = ConversationService(
            conversation_repo=FakeConversationRepo(conversation),
            message_repo=FakeMessageRepo(),
            report_repo=FakeReportRepo(),
        )

        response = service.post_message(
            user_id="user-1",
            conversation_id="conv-1",
            message="主要风险是什么？",
        )

        self.assertEqual(len(response.messages), 2)
        self.assertIn("当前会话还没有生成可解读的完整报告", response.messages[-1].content)
        self.assertIsNone(response.reportId)

    def test_post_message_with_report_falls_back_to_summary_when_llm_unavailable(self):
        conversation = {
            "id": "conv-2",
            "userId": "user-1",
            "status": "report_ready",
            "lastReportId": "report-2",
        }
        report = {
            "id": "report-2",
            "conversationId": "conv-2",
            "userId": "user-1",
            "summary": "报告认为核心风险在于估值偏高和短期波动。",
            "executiveSummary": "报告认为核心风险在于估值偏高和短期波动。",
            "contentMarkdown": "# Report\n\nRisk section",
            "stockSymbol": "AAPL",
            "title": "AAPL 分析报告",
        }
        service = ConversationService(
            conversation_repo=FakeConversationRepo(conversation),
            message_repo=FakeMessageRepo(),
            report_repo=FakeReportRepo(report),
        )
        service._build_followup_llm = lambda: None  # type: ignore[attr-defined]

        response = service.post_message(
            user_id="user-1",
            conversation_id="conv-2",
            message="主要风险是什么？",
        )

        self.assertEqual(response.reportId, "report-2")
        self.assertIn("执行摘要", response.messages[-1].content)
        self.assertIn("主要风险是什么", response.messages[-1].content)


if __name__ == "__main__":
    unittest.main()
