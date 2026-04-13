from __future__ import annotations

from fastapi import HTTPException, status

from ta_service.contracts.conversations import (
    build_conversation_detail,
    build_message,
    build_conversation_summary,
)
from ta_service.models.message_types import MessageType
from ta_service.models.conversation import (
    ConversationDetail,
    ConversationSummary,
    PostConversationMessageResponse,
)
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.repos.reports import ReportRepository
from ta_service.services.conversation_state_machine import ConversationStateMachine
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.factory import create_llm_client


class ConversationService:
    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        report_repo: ReportRepository,
        task_repo: AnalysisTaskRepository,
        state_machine: ConversationStateMachine,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.report_repo = report_repo
        self.task_repo = task_repo
        self.state_machine = state_machine

    def create_conversation(self, *, user_id: str, title: str | None) -> ConversationSummary:
        document = self.conversation_repo.create(user_id=user_id, title=title or "新会话")
        return build_conversation_summary(document)

    def list_conversations(self, *, user_id: str) -> list[ConversationSummary]:
        return [
            build_conversation_summary(document)
            for document in self.conversation_repo.list_for_user(user_id)
        ]

    def get_conversation(self, *, user_id: str, conversation_id: str) -> ConversationDetail | None:
        document = self.conversation_repo.get_for_user(conversation_id=conversation_id, user_id=user_id)
        if not document:
            return None
        messages = self.message_repo.list_for_conversation(conversation_id)
        task_doc: dict | None = None
        if document.get("status") == "analyzing" and document.get("currentTaskId"):
            task_doc = self.task_repo.get_by_task_id(document["currentTaskId"])
        return build_conversation_detail(document, messages, task_doc)

    def delete_conversation(self, *, user_id: str, conversation_id: str) -> None:
        conversation = self.conversation_repo.get_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if conversation.get("status") == "analyzing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a conversation while analysis is running",
            )
        self.conversation_repo.delete(conversation_id=conversation_id, user_id=user_id)
        self.message_repo.delete_for_conversation(conversation_id=conversation_id)

    def post_message(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str,
    ) -> PostConversationMessageResponse:
        conversation = self.conversation_repo.get_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        conv_status = conversation.get("status")
        if conv_status == "analyzing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is still running for this conversation",
            )
        if conv_status not in ("report_ready", "report_explaining"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"post_message not allowed in conversation status: {conv_status}",
            )

        user_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="user",
            message_type=MessageType.TEXT,
            content=message.strip(),
        )
        report = (
            self.report_repo.get_for_user(
                report_id=conversation.get("lastReportId"),
                user_id=user_id,
            )
            if conversation.get("lastReportId")
            else self.report_repo.get_latest_for_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )
        assistant_text = self._build_followup_reply(message=message, report=report)
        assistant_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            message_type=MessageType.TEXT,
            content=assistant_text,
        )
        next_status = "report_explaining" if report else "idle"
        self.state_machine.transition(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status=next_status,
        )
        return PostConversationMessageResponse(
            messages=[build_message(user_message), build_message(assistant_message)],
            reportId=report["id"] if report else None,
        )

    def _build_followup_reply(self, *, message: str, report: dict | None) -> str:
        if not report:
            return (
                "当前会话还没有生成可解读的完整报告。请先发起一次分析，报告生成后我再继续围绕结果回答。"
            )

        llm = self._build_followup_llm()
        prompt = self._build_followup_prompt(message=message, report=report)
        if llm is None:
            return self._build_fallback_reply(message=message, report=report)

        try:
            response = llm.invoke(prompt)
        except Exception:
            return self._build_fallback_reply(message=message, report=report)

        content = getattr(response, "content", "") if response else ""
        normalized = content.strip() if isinstance(content, str) else ""
        return normalized or self._build_fallback_reply(message=message, report=report)

    def _build_followup_llm(self):
        provider = DEFAULT_CONFIG.get("llm_provider")
        model = DEFAULT_CONFIG.get("quick_think_llm")
        if not provider or not model:
            return None

        try:
            return create_llm_client(
                provider=provider,
                model=model,
                base_url=DEFAULT_CONFIG.get("backend_url"),
                timeout=DEFAULT_CONFIG.get("llm_timeout", 120),
                max_retries=DEFAULT_CONFIG.get("llm_max_retries", 1),
            ).get_llm()
        except Exception:
            return None

    def _build_followup_prompt(self, *, message: str, report: dict) -> str:
        executive_summary = (report.get("executiveSummary") or "").strip()
        content_markdown = (report.get("contentMarkdown") or "").strip()
        grounded_content = content_markdown[:12000]
        return f"""
你是 InsightTrader 移动端的一期报告解读助手。请仅基于给定报告内容回答用户追问，禁止编造报告中没有的信息。

回答要求：
1. 使用简体中文。
2. 优先直接回答用户问题，再给出 2-4 条要点。
3. 如果报告没有足够信息支撑答案，要明确说明"报告中没有直接给出"，然后给出基于现有内容的最接近结论。
4. 不要提及你是模型或引用提示词。

股票：{report.get("stockSymbol", "未知")}
报告标题：{report.get("title", "未命名报告")}

执行摘要：
{executive_summary or "无"}

完整报告节选：
{grounded_content or "无"}

用户问题：
{message.strip()}
""".strip()

    def _build_fallback_reply(self, *, message: str, report: dict) -> str:
        summary = (report.get("executiveSummary") or report.get("summary") or "").strip()
        if not summary:
            return (
                f"我已记录你的问题：{message.strip()}。当前报告已生成，但缺少可直接引用的执行摘要，"
                "建议先打开完整报告查看细节，我后续会结合完整内容继续完善解读能力。"
            )
        return (
            f"我已记录你的问题：{message.strip()}。\n\n"
            f"先基于当前执行摘要给你一个最接近的回答：\n{summary}\n\n"
            "如果你想看更完整的依据，可以打开完整报告继续追问具体段落。"
        )
