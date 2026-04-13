from __future__ import annotations

import logging
import os
from collections.abc import Callable

from fastapi import HTTPException, status

from ta_service.config.settings import Settings
from ta_service.contracts.analysis import build_analysis_status
from ta_service.models.analysis import AnalysisTaskStatusResponse, CreateAnalysisTaskRequest
from ta_service.models.message_types import MessageType
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.repos.reports import ReportRepository
from ta_service.services.conversation_state_machine import ConversationStateMachine
from ta_service.workers.launcher import spawn_analysis_task_runner
from ta_service.workers.queue import AnalysisJobQueue

logger = logging.getLogger(__name__)

_DEBUG_SKIP_ANALYSIS = os.getenv("TA_SERVICE_DEBUG_SKIP_ANALYSIS", "").lower() in ("1", "true", "yes")


class AnalysisService:
    def __init__(
        self,
        *,
        task_repo: AnalysisTaskRepository,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        report_repo: ReportRepository,
        queue: AnalysisJobQueue,
        settings: Settings,
        state_machine: ConversationStateMachine,
        task_launcher: Callable[[str], object] = spawn_analysis_task_runner,
    ):
        self.task_repo = task_repo
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.report_repo = report_repo
        self.queue = queue
        self.settings = settings
        self.state_machine = state_machine
        self.task_launcher = task_launcher

    def get_task_status(self, *, task_id: str, user_id: str) -> AnalysisTaskStatusResponse | None:
        document = self.task_repo.get_for_user(task_id=task_id, user_id=user_id)
        if not document:
            return None
        return build_analysis_status(document)

    def create_task(
        self,
        *,
        user_id: str,
        payload: CreateAnalysisTaskRequest,
    ) -> AnalysisTaskStatusResponse:
        conversation = self.conversation_repo.get_for_user(
            conversation_id=payload.conversationId,
            user_id=user_id,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if conversation.get("status") != "ready_to_analyze":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation is not ready for analysis",
            )

        confirmed_stock = conversation.get("confirmedStock") or {}
        confirmed_ticker = (confirmed_stock.get("ticker") or "").strip().upper()
        if not confirmed_ticker:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation does not have a confirmed stock target",
            )
        if payload.ticker.strip().upper() != confirmed_ticker:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis ticker does not match the confirmed stock target",
            )

        active_task = self.task_repo.get_active_for_user(user_id)
        if active_task:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A task is already running for this user",
            )

        if not self.queue.acquire_user_lock(user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to acquire analysis lock for this user",
            )

        task_doc = self.launch_analysis(
            user_id=user_id,
            conversation_id=payload.conversationId,
            ticker=payload.ticker,
            trade_date=payload.tradeDate,
            prompt=payload.prompt,
            selected_analysts=payload.selectedAnalysts,
        )
        return build_analysis_status(task_doc)

    def launch_analysis(
        self,
        *,
        user_id: str,
        conversation_id: str,
        ticker: str,
        trade_date: str,
        prompt: str,
        selected_analysts: list[str] | None = None,
    ) -> dict:
        """
        内部方法：已持锁、已校验状态后直接创建并启动分析任务。
        返回任务文档 dict，调用方可从中取进度字段。
        """
        document = self.task_repo.create(
            user_id=user_id,
            conversation_id=conversation_id,
            ticker=ticker,
            trade_date=trade_date,
            prompt=prompt,
            selected_analysts=selected_analysts or [],
        )

        self.message_repo.create(
            conversation_id=conversation_id,
            role="system",
            message_type=MessageType.TASK_STATUS,
            content={"text": "已收到分析请求，正在准备任务", "stageId": None},
        )
        title = " ".join(prompt.strip().split())[:30] if prompt and prompt.strip() else f"{ticker} 分析"

        self.state_machine.transition(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status="analyzing",
            title=title,
            task_id=document["taskId"],
        )

        if _DEBUG_SKIP_ANALYSIS:
            logger.info(
                "debug_skip_analysis task_id=%s ticker=%s conversation_id=%s",
                document["taskId"], ticker, conversation_id,
            )
            self.queue.release_user_lock(user_id)
            self.task_repo.update_status(
                document["taskId"],
                status="completed",
                currentStep="[DEV] 已跳过分析",
                message="[DEV] TA_SERVICE_DEBUG_SKIP_ANALYSIS=true，已跳过 worker 启动",
            )
            self.state_machine.transition_unchecked(
                conversation_id=conversation_id,
                user_id=user_id,
                to_status="report_ready",
                task_id=document["taskId"],
            )
            document["status"] = "completed"
            document["currentStep"] = "[DEV] 已跳过分析"
            document["message"] = "[DEV] TA_SERVICE_DEBUG_SKIP_ANALYSIS=true，已跳过 worker 启动"
            return document

        try:
            self.task_launcher(document["taskId"])
            self.task_repo.update_status(
                document["taskId"],
                status="pending",
                currentStep="任务已启动",
                message="任务已启动",
            )
            document["status"] = "pending"
            document["currentStep"] = "任务已启动"
            document["message"] = "任务已启动"
        except Exception as exc:
            self.queue.release_user_lock(user_id)
            self.task_repo.update_status(
                document["taskId"],
                status="failed",
                currentStep="任务启动失败",
                message=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to launch analysis task runner",
            ) from exc
        return document
