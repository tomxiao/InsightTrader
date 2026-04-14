from __future__ import annotations

import logging

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
from ta_service.models.report_insight import ReportInsightContext
from ta_service.config.settings import Settings
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.services.conversation_state_machine import ConversationStateMachine
from ta_service.services.report_context_loader import ReportContextLoader
from ta_service.services.report_insight_agent import ReportInsightAgent

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        task_repo: AnalysisTaskRepository,
        state_machine: ConversationStateMachine,
        settings: Settings,
        report_context_loader: ReportContextLoader,
        report_insight_agent: ReportInsightAgent,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.task_repo = task_repo
        self.state_machine = state_machine
        self.settings = settings
        self.report_context_loader = report_context_loader
        self.report_insight_agent = report_insight_agent

    def create_conversation(self, *, user_id: str, title: str | None) -> ConversationSummary:
        active_task = self.task_repo.get_active_for_user(
            user_id, ttl_seconds=self.settings.analysis_task_ttl_seconds
        )
        if active_task:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot create a new conversation while analysis is running",
            )
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

        all_messages = self.message_repo.list_for_conversation(conversation_id)

        user_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="user",
            message_type=MessageType.TEXT,
            content=message.strip(),
        )

        insight_context = self._build_insight_context(
            conversation=conversation,
            all_messages=all_messages,
            question=message.strip(),
        )
        result = self.report_insight_agent.answer(context=insight_context)

        assistant_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            message_type=MessageType.INSIGHT_REPLY,
            content=result.answer,
        )
        self.state_machine.transition(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status="report_explaining",
        )
        return PostConversationMessageResponse(
            messages=[build_message(user_message), build_message(assistant_message)],
        )

    def _build_insight_context(
        self,
        *,
        conversation: dict,
        all_messages: list[dict],
        question: str,
    ) -> ReportInsightContext:
        """构建 ReportInsightAgent 所需的上下文。

        正常路径：传入 trace_dir + available_sections，Agent 按需调工具读章节。
        降级路径：无 traceDir 时用 SUMMARY_CARD 文本填充 report_sections。
        """
        ticker = ""
        trade_date = ""
        trace_dir: str | None = None
        available_sections: list[str] = []
        report_sections: dict[str, str] = {}

        task_id = conversation.get("currentTaskId")
        if task_id:
            task_doc = self.task_repo.get_by_task_id(task_id)
            if task_doc:
                trace_dir = task_doc.get("traceDir") or None
                ticker = task_doc.get("symbol") or ""
                trade_date = task_doc.get("tradeDate") or ""
                if trace_dir:
                    available_sections = self.report_context_loader.list_available_sections(
                        trace_dir=trace_dir
                    )

        # 降级：无磁盘报告时使用 SUMMARY_CARD 文本作为单章节上下文
        if not trace_dir and not available_sections:
            summary_text = self._get_summary_text(all_messages=all_messages)
            if summary_text:
                report_sections = {"executive_summary": summary_text}
                logger.info(
                    "post_message: using summary_card fallback conversation_id=%s",
                    conversation.get("id"),
                )

        history = self._build_conversation_history(all_messages=all_messages)

        return ReportInsightContext(
            question=question,
            ticker=ticker,
            trade_date=trade_date,
            trace_dir=trace_dir,
            available_sections=available_sections,
            report_sections=report_sections,
            conversation_history=history,
        )

    def _get_summary_text(self, *, all_messages: list[dict]) -> str | None:
        """从消息列表中获取最新的 SUMMARY_CARD 内容。"""
        for msg in reversed(all_messages):
            if msg.get("messageType") == MessageType.SUMMARY_CARD:
                content = msg.get("content")
                if isinstance(content, dict):
                    return content.get("text") or None
                if isinstance(content, str):
                    return content or None
        return None

    def _build_conversation_history(self, *, all_messages: list[dict]) -> list[dict]:
        """提取最近 N 轮 user/assistant 对话消息作为多轮历史。"""
        max_turns = self.settings.followup_history_turns
        text_messages = [
            msg for msg in all_messages
            if msg.get("role") in ("user", "assistant")
            and msg.get("messageType") in (MessageType.TEXT, MessageType.INSIGHT_REPLY)
        ]
        recent = text_messages[-max_turns:] if len(text_messages) > max_turns else text_messages
        return [
            {"role": msg["role"], "content": msg.get("content", "")}
            for msg in recent
        ]
