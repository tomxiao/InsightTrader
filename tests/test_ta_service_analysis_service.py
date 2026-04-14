import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from ta_service.models.analysis import CreateAnalysisTaskRequest
from ta_service.services.analysis_service import AnalysisService


class FakeTaskRepo:
    def __init__(self):
        self.created = None
        self.status_updates: list[dict] = []

    def get_active_for_user(self, user_id: str, ttl_seconds: int = 7200):
        return None

    def create(
        self,
        *,
        user_id: str,
        conversation_id: str,
        ticker: str,
        trade_date: str,
        prompt: str | None,
        selected_analysts=None,
    ):
        self.created = {
            "taskId": "task-1",
            "userId": user_id,
            "conversationId": conversation_id,
            "ticker": ticker,
            "tradeDate": trade_date,
            "prompt": prompt,
            "selectedAnalysts": selected_analysts,
            "status": "created",
            "currentStep": "",
            "message": "",
        }
        return dict(self.created)

    def update_status(self, task_id: str, **fields) -> None:
        fields["taskId"] = task_id
        self.status_updates.append(fields)


class FakeConversationRepo:
    def __init__(self, conversation: dict):
        self.conversation = conversation

    def get_for_user(self, *, conversation_id: str, user_id: str):
        if self.conversation["id"] == conversation_id and self.conversation["userId"] == user_id:
            return self.conversation
        return None


class FakeMessageRepo:
    def __init__(self):
        self.created: list[dict] = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return kwargs


class FakeStateMachine:
    def transition(self, **kwargs):
        pass

    def transition_unchecked(self, **kwargs):
        pass


class FakeLauncher:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls: list[str] = []

    def __call__(self, task_id: str) -> None:
        self.calls.append(task_id)
        if self.should_fail:
            raise RuntimeError("boom")


class AnalysisServiceTests(unittest.TestCase):
    def _build_service(self, conversation: dict, *, should_fail: bool = False):
        task_repo = FakeTaskRepo()
        conversation_repo = FakeConversationRepo(conversation)
        message_repo = FakeMessageRepo()
        state_machine = FakeStateMachine()
        launcher = FakeLauncher(should_fail=should_fail)
        service = AnalysisService(
            task_repo=task_repo,
            conversation_repo=conversation_repo,
            message_repo=message_repo,
            settings=SimpleNamespace(analysis_task_ttl_seconds=7200),
            state_machine=state_machine,
            task_launcher=launcher,
        )
        return service, task_repo, conversation_repo, message_repo, launcher

    def test_create_task_rejects_unconfirmed_ticker(self):
        conversation = {
            "id": "conv-1",
            "userId": "user-1",
            "status": "ready_to_analyze",
            "confirmedStock": {"ticker": "AAPL", "name": "Apple Inc."},
        }
        service, *_ = self._build_service(conversation)

        with self.assertRaises(HTTPException) as ctx:
            service.create_task(
                user_id="user-1",
                payload=CreateAnalysisTaskRequest(
                    conversationId="conv-1",
                    ticker="TSLA",
                    tradeDate="2026-04-11",
                    prompt="分析苹果",
                ),
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("confirmed stock target", ctx.exception.detail)

    def test_create_task_uses_mock_launcher_and_returns_pending_status(self):
        conversation = {
            "id": "conv-1",
            "userId": "user-1",
            "status": "ready_to_analyze",
            "confirmedStock": {"ticker": "AAPL", "name": "Apple Inc."},
        }
        service, task_repo, _conv_repo, message_repo, launcher = self._build_service(conversation)

        response = service.create_task(
            user_id="user-1",
            payload=CreateAnalysisTaskRequest(
                conversationId="conv-1",
                ticker="AAPL",
                tradeDate="2026-04-11",
                prompt="分析苹果",
            ),
        )

        self.assertEqual(response.status, "pending")
        self.assertEqual(launcher.calls, ["task-1"])
        last_update = task_repo.status_updates[-1]
        self.assertEqual(last_update.get("status"), "pending")
        self.assertEqual(message_repo.created[-1]["message_type"], "task_status")

    def test_create_task_marks_failed_when_mock_launcher_errors(self):
        conversation = {
            "id": "conv-1",
            "userId": "user-1",
            "status": "ready_to_analyze",
            "confirmedStock": {"ticker": "AAPL", "name": "Apple Inc."},
        }
        service, task_repo, _conv_repo, _msg_repo, launcher = self._build_service(
            conversation,
            should_fail=True,
        )

        with self.assertRaises(HTTPException) as ctx:
            service.create_task(
                user_id="user-1",
                payload=CreateAnalysisTaskRequest(
                    conversationId="conv-1",
                    ticker="AAPL",
                    tradeDate="2026-04-11",
                    prompt="分析苹果",
                ),
            )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(launcher.calls, ["task-1"])
        last_update = task_repo.status_updates[-1]
        self.assertEqual(last_update.get("status"), "failed")


if __name__ == "__main__":
    unittest.main()
