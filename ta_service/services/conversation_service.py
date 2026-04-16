from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fastapi import HTTPException, status

from ta_service.config.settings import Settings
from ta_service.contracts.conversations import (
    build_conversation_detail,
    build_conversation_summary,
    build_message,
)
from ta_service.models.conversation import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    PostConversationMessageResponse,
)
from ta_service.models.message_types import MessageType
from ta_service.models.report_insight import ReportInsightContext
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
        document = self.conversation_repo.get_for_user(
            conversation_id=conversation_id, user_id=user_id
        )
        if not document:
            return None
        messages = self.message_repo.list_for_conversation(conversation_id)
        task_doc: dict | None = None
        if document.get("currentTaskId"):
            task_doc = self.task_repo.get_by_task_id(document["currentTaskId"])
        return build_conversation_detail(document, messages, task_doc)

    def delete_conversation(self, *, user_id: str, conversation_id: str) -> None:
        conversation = self.conversation_repo.get_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
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
        username: str,
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
        self._write_insight_reply_audit_log(
            username=username,
            conversation=conversation,
            context=insight_context,
            question=message.strip(),
            answer=result.answer,
            source_sections=result.source_sections,
            routing_intent=result.routing_intent,
            routing_primary_section=result.routing_primary_section,
            routing_fallback_sections=result.routing_fallback_sections,
            routing_reason=result.routing_reason,
            is_answerable=result.is_answerable,
            llm_router_ms=result.llm_router_ms,
            llm_reply_ms=result.llm_reply_ms,
        )
        return PostConversationMessageResponse(
            messages=[build_message(user_message), build_message(assistant_message)],
        )

    def stream_post_message(
        self,
        *,
        user_id: str,
        username: str,
        conversation_id: str,
        message: str,
    ) -> Iterator[dict[str, object]]:
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

        yield {
            "event": "started",
            "userMessage": build_message(user_message).model_dump(),
        }

        stream = self.report_insight_agent.answer_events(context=insight_context)
        result = None
        while True:
            try:
                payload = next(stream)
                yield payload
            except StopIteration as stop:
                result = stop.value
                break

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Insight reply stream did not return a result",
            )

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
        self._write_insight_reply_audit_log(
            username=username,
            conversation=conversation,
            context=insight_context,
            question=message.strip(),
            answer=result.answer,
            source_sections=result.source_sections,
            routing_intent=result.routing_intent,
            routing_primary_section=result.routing_primary_section,
            routing_fallback_sections=result.routing_fallback_sections,
            routing_reason=result.routing_reason,
            is_answerable=result.is_answerable,
            llm_router_ms=result.llm_router_ms,
            llm_reply_ms=result.llm_reply_ms,
        )
        yield {
            "event": "completed",
            "assistantMessage": build_message(assistant_message).model_dump(),
        }

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
        summary_text: str | None = self._get_summary_text(all_messages=all_messages)
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
            if summary_text:
                report_sections = {"executive_summary": summary_text}
                logger.info(
                    "post_message: using summary_card fallback conversation_id=%s",
                    conversation.get("id"),
                )

        history = self._build_conversation_history(all_messages=all_messages)

        return ReportInsightContext(
            conversation_id=conversation.get("id", ""),
            question=question,
            ticker=ticker,
            trade_date=trade_date,
            trace_dir=trace_dir,
            available_sections=available_sections,
            summary_text=summary_text,
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
        """提取最近两轮 user/assistant 对话消息，避免多轮时不断重复扩写。"""
        max_messages = min(self.settings.followup_history_turns, 4)
        text_messages = [
            msg
            for msg in all_messages
            if msg.get("role") in ("user", "assistant")
            and msg.get("messageType") in (MessageType.TEXT, MessageType.INSIGHT_REPLY)
        ]
        recent = (
            text_messages[-max_messages:] if len(text_messages) > max_messages else text_messages
        )
        return [{"role": msg["role"], "content": msg.get("content", "")} for msg in recent]

    def _write_insight_reply_audit_log(
        self,
        *,
        username: str,
        conversation: dict,
        context: ReportInsightContext,
        question: str,
        answer: str,
        source_sections: list[str],
        routing_intent: str | None,
        routing_primary_section: str | None,
        routing_fallback_sections: list[str],
        routing_reason: str | None,
        is_answerable: bool,
        llm_router_ms: float | None,
        llm_reply_ms: float | None,
    ) -> None:
        try:
            user_log_dir = self.settings.logs_root / _sanitize_username(username)
            user_log_dir.mkdir(parents=True, exist_ok=True)
            log_path = user_log_dir / "insight_reply.jsonl"
            report_dir = _resolve_report_dir_from_trace_dir(
                trace_dir=context.trace_dir,
                reports_root=self.settings.reports_root,
            )
            payload = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "username": username,
                "conversation_title": conversation.get("title") or "",
                "conversation_id": context.conversation_id,
                "ticker": context.ticker,
                "trade_date": context.trade_date,
                "report_dir": str(report_dir) if report_dir else None,
                "trace_dir": context.trace_dir,
                "user_input": question,
                "gating": {
                    "intent": routing_intent,
                    "primary_section": routing_primary_section,
                    "fallback_sections": routing_fallback_sections,
                    "reason": routing_reason,
                },
                "source_sections": source_sections,
                "is_answerable": is_answerable,
                "llm_router_ms": llm_router_ms,
                "llm_reply_ms": llm_reply_ms,
                "reply": answer,
            }
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning(
                "post_message: failed to write insight reply audit log conversation_id=%s error=%s",
                context.conversation_id,
                exc,
            )


def _sanitize_username(username: str) -> str:
    value = (username or "").strip() or "unknown_user"
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)


def _resolve_report_dir_from_trace_dir(*, trace_dir: str | None, reports_root: Path) -> Path | None:
    if not trace_dir:
        return None
    return reports_root / Path(trace_dir).name
