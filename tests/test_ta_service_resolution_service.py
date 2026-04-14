import unittest

from fastapi import HTTPException

from ta_service.models.resolution import (
    AgentResolutionResult,
    ResolutionAgentContext,
    ResolutionCandidate,
    ResolutionConfirmRequest,
)
from ta_service.services.resolution_service import ResolutionService


class FakeConversationRepo:
    def __init__(self, conversation: dict):
        self.conversation = conversation

    def get_for_user(self, *, conversation_id: str, user_id: str):
        if self.conversation["id"] == conversation_id and self.conversation["userId"] == user_id:
            return self.conversation
        return None

    def update_resolution_state(
        self,
        *,
        conversation_id: str,
        user_id: str,
        status: str,
        pending_resolution: dict | None,
        confirmed_stock: dict | None = None,
        confirmed_analysis_prompt: str | None = None,
    ) -> None:
        if self.conversation["id"] != conversation_id or self.conversation["userId"] != user_id:
            return
        self.conversation["status"] = status
        self.conversation["pendingResolution"] = pending_resolution
        self.conversation["confirmedStock"] = confirmed_stock
        self.conversation["confirmedAnalysisPrompt"] = confirmed_analysis_prompt


class FakeMessageRepo:
    def __init__(self):
        self.created: list[dict] = []

    def create(self, *, conversation_id: str, role: str, content, message_type: str = "text"):
        document = {
            "id": f"message-{len(self.created) + 1}",
            "conversationId": conversation_id,
            "role": role,
            "messageType": message_type,
            "content": content,
            "createdAt": "2026-04-11T12:00:00+00:00",
        }
        self.created.append(document)
        return document


class FakeResolutionAgent:
    def __init__(self, results: list[AgentResolutionResult]):
        self.results = list(results)
        self.contexts: list[ResolutionAgentContext] = []

    def resolve(self, *, context: ResolutionAgentContext) -> AgentResolutionResult:
        self.contexts.append(context)
        if not self.results:
            raise AssertionError("No more fake resolution results configured")
        return self.results.pop(0)


class FakeStockLookupGateway:
    def __init__(self, profiles: dict[str, ResolutionCandidate]):
        self.profiles = {ticker.upper(): candidate for ticker, candidate in profiles.items()}

    def get_stock_profile(self, *, ticker: str) -> ResolutionCandidate | None:
        return self.profiles.get(ticker.upper())


class ResolutionServiceTests(unittest.TestCase):
    def setUp(self):
        self.apple = ResolutionCandidate(
            ticker="AAPL",
            name="Apple Inc.",
            market="US",
            exchange="NASDAQ",
        )
        self.tencent = ResolutionCandidate(
            ticker="0700.HK",
            name="Tencent Holdings Limited",
            market="HK",
            exchange="HKEX",
        )
        self.conversation = {
            "id": "conv-1",
            "userId": "user-1",
            "status": "idle",
            "pendingResolution": None,
            "confirmedStock": None,
            "confirmedAnalysisPrompt": None,
        }
        self.conversation_repo = FakeConversationRepo(self.conversation)
        self.message_repo = FakeMessageRepo()

    def _create_service(self, results: list[AgentResolutionResult]) -> ResolutionService:
        from types import SimpleNamespace

        class FakeTaskRepo:
            def get_active_for_user(self, user_id: str, ttl_seconds: int = 7200):
                return None

        class FakeStateMachine:
            def transition(self, **kwargs):
                pass

        class FakeAnalysisService:
            settings = SimpleNamespace(analysis_task_ttl_seconds=7200)

            def _check_active_task(self, user_id: str):
                return None

        gateway = FakeStockLookupGateway(
            {
                "AAPL": self.apple,
                "0700.HK": self.tencent,
            }
        )
        agent = FakeResolutionAgent(results)
        service = ResolutionService(
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            resolution_agent=agent,
            stock_lookup_gateway=gateway,
            analysis_service=FakeAnalysisService(),
            task_repo=FakeTaskRepo(),
            state_machine=FakeStateMachine(),
        )
        service._fake_agent = agent  # type: ignore[attr-defined]
        return service

    def test_resolution_confirm_flow_moves_conversation_to_ready(self):
        service = self._create_service(
            [
                AgentResolutionResult(
                    status="need_confirm",
                    assistantReply="你想分析的是 Apple Inc.（AAPL）吗？",
                    stock=self.apple,
                    candidates=[self.apple],
                    focusPoints=["估值"],
                )
            ]
        )

        response = service.resolve_message(
            user_id="user-1",
            conversation_id="conv-1",
            message="分析苹果，重点看估值",
        )

        self.assertEqual(response.status, "need_confirm")
        self.assertEqual(response.ticker, "AAPL")
        self.assertEqual(self.conversation["status"], "collecting_inputs")
        self.assertIsNotNone(self.conversation["pendingResolution"])
        self.assertIsNone(self.conversation["confirmedStock"])

        confirmed = service.confirm_resolution(
            user_id="user-1",
            conversation_id="conv-1",
            payload=ResolutionConfirmRequest(action="confirm", resolutionId=response.resolutionId or ""),
        )

        self.assertEqual(confirmed.status, "resolved")
        self.assertEqual(confirmed.ticker, "AAPL")
        self.assertEqual(self.conversation["status"], "ready_to_analyze")
        self.assertIsNone(self.conversation["pendingResolution"])
        self.assertEqual(self.conversation["confirmedStock"]["ticker"], "AAPL")
        self.assertIn("分析苹果", self.conversation["confirmedAnalysisPrompt"])

    def test_disambiguation_select_flow_persists_selected_stock(self):
        service = self._create_service(
            [
                AgentResolutionResult(
                    status="need_disambiguation",
                    assistantReply="我找到了多个可能的股票，请选择。",
                    candidates=[self.apple, self.tencent],
                    focusPoints=["催化"],
                )
            ]
        )

        response = service.resolve_message(
            user_id="user-1",
            conversation_id="conv-1",
            message="分析腾讯或苹果，关注催化",
        )
        selected = service.confirm_resolution(
            user_id="user-1",
            conversation_id="conv-1",
            payload=ResolutionConfirmRequest(
                action="select",
                resolutionId=response.resolutionId or "",
                ticker="0700.HK",
            ),
        )

        self.assertEqual(selected.status, "resolved")
        self.assertEqual(selected.ticker, "0700.HK")
        self.assertEqual(self.conversation["confirmedStock"]["ticker"], "0700.HK")

    def test_stale_resolution_id_is_rejected(self):
        service = self._create_service(
            [
                AgentResolutionResult(
                    status="need_confirm",
                    assistantReply="你想分析的是 Apple Inc.（AAPL）吗？",
                    stock=self.apple,
                    candidates=[self.apple],
                )
            ]
        )
        service.resolve_message(user_id="user-1", conversation_id="conv-1", message="分析苹果")

        with self.assertRaises(HTTPException) as ctx:
            service.confirm_resolution(
                user_id="user-1",
                conversation_id="conv-1",
                payload=ResolutionConfirmRequest(action="confirm", resolutionId="stale-id"),
            )

        self.assertEqual(ctx.exception.status_code, 409)

    def test_round_limit_returns_failed_without_invoking_agent_third_time(self):
        service = self._create_service(
            [
                AgentResolutionResult(status="collect_more", assistantReply="请补充更多信息。"),
                AgentResolutionResult(status="collect_more", assistantReply="仍需更多信息。"),
            ]
        )

        service.resolve_message(user_id="user-1", conversation_id="conv-1", message="分析一个模糊公司")
        service.resolve_message(user_id="user-1", conversation_id="conv-1", message="还是这个公司")
        response = service.resolve_message(user_id="user-1", conversation_id="conv-1", message="继续帮我猜")

        self.assertEqual(response.status, "failed")
        self.assertEqual(len(service._fake_agent.contexts), 2)  # type: ignore[attr-defined]
        self.assertIsNone(self.conversation["pendingResolution"])

    def test_second_round_context_includes_pending_prompt_and_summary(self):
        service = self._create_service(
            [
                AgentResolutionResult(status="collect_more", assistantReply="请补充股票名称。"),
                AgentResolutionResult(
                    status="need_confirm",
                    assistantReply="你想分析的是 Apple Inc.（AAPL）吗？",
                    stock=self.apple,
                    candidates=[self.apple],
                ),
            ]
        )

        service.resolve_message(user_id="user-1", conversation_id="conv-1", message="重点看估值")
        service.resolve_message(user_id="user-1", conversation_id="conv-1", message="苹果")

        second_context = service._fake_agent.contexts[1]  # type: ignore[attr-defined]
        self.assertIn("重点看估值", second_context.analysisPrompt)
        self.assertIn("苹果", second_context.analysisPrompt)
        self.assertEqual(second_context.pendingResolution.status, "collect_more")
        self.assertTrue(second_context.priorResolutionSummary)


if __name__ == "__main__":
    unittest.main()
