from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import HTTPException, status

from ta_service.contracts.conversations import build_message, build_task_progress
from ta_service.models.message_types import MessageType
from ta_service.models.resolution import (
    AgentResolutionResult,
    PendingResolutionSnapshot,
    ResolutionAgentContext,
    ResolutionCandidate,
    ResolutionConfirmRequest,
    ResolutionResponse,
)
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.services.analysis_service import AnalysisService
from ta_service.services.conversation_state_machine import ConversationStateMachine
from ta_service.services.resolution_agent import ResolutionAgent
from ta_service.services.stock_lookup_gateway import StockLookupError, StockLookupGateway
from ta_service.workers.queue import AnalysisJobQueue

logger = logging.getLogger(__name__)

MAX_RESOLUTION_ROUNDS = 2

_TODAY = __import__("datetime").date.today


class ResolutionService:
    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        resolution_agent: ResolutionAgent,
        stock_lookup_gateway: StockLookupGateway,
        analysis_service: AnalysisService,
        task_repo: AnalysisTaskRepository,
        queue: AnalysisJobQueue,
        state_machine: ConversationStateMachine,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.resolution_agent = resolution_agent
        self.stock_lookup_gateway = stock_lookup_gateway
        self.analysis_service = analysis_service
        self.task_repo = task_repo
        self.queue = queue
        self.state_machine = state_machine

    def resolve_message(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str,
    ) -> ResolutionResponse:
        conversation = self._get_conversation(user_id=user_id, conversation_id=conversation_id)
        self._ensure_resolution_allowed(conversation)

        current_message = message.strip()
        existing_pending = _parse_pending_snapshot(conversation.get("pendingResolution"))
        round_number = (existing_pending.round if existing_pending else 0) + 1
        resolution_id = str(uuid4())
        analysis_prompt = _compose_analysis_prompt(existing_pending=existing_pending, message=current_message)

        user_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="user",
            message_type=MessageType.TEXT,
            content=current_message,
        )

        if round_number > MAX_RESOLUTION_ROUNDS:
            result = AgentResolutionResult(
                status="failed",
                assistantReply=(
                    "我暂时还无法准确定位你想分析的股票。请直接提供公司全名或股票代码，"
                    "例如 AAPL、0700.HK、300750.SZ。"
                ),
                terminate=True,
            )
        else:
            result = self.resolution_agent.resolve(
                context=ResolutionAgentContext(
                    currentMessage=current_message,
                    currentRound=round_number,
                    priorResolutionSummary=_build_prior_summary(existing_pending),
                    analysisPrompt=analysis_prompt,
                    pendingResolution=existing_pending,
                )
            )

        assistant_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            message_type=MessageType.TICKER_RESOLUTION,
            content=_build_resolution_message_content(
                resolution_id=resolution_id,
                result=result,
                analysis_prompt=analysis_prompt,
            ),
        )

        pending_resolution = _build_pending_resolution(
            resolution_id=resolution_id,
            round_number=round_number,
            result=result,
            original_message=current_message,
            analysis_prompt=analysis_prompt,
        )
        confirmed_stock = result.stock.model_dump() if result.status == "resolved" and result.stock else None
        confirmed_analysis_prompt = analysis_prompt if result.status == "resolved" else None
        conversation_status = "ready_to_analyze" if result.status == "resolved" else "collecting_inputs"

        self.state_machine.transition(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status=conversation_status,
            pending_resolution=pending_resolution.model_dump(mode="json") if pending_resolution else None,
            confirmed_stock=confirmed_stock,
            confirmed_analysis_prompt=confirmed_analysis_prompt,
        )
        logger.info(
            "resolution_completed conversation_id=%s resolution_id=%s round=%s status=%s candidate_count=%s",
            conversation_id,
            resolution_id,
            round_number,
            result.status,
            len(result.candidates),
        )

        task_progress = None
        if result.status == "resolved" and confirmed_stock:
            ticker = confirmed_stock.get("ticker", "")
            task_doc = self._try_launch_analysis(
                user_id=user_id,
                conversation_id=conversation_id,
                ticker=ticker,
                prompt=analysis_prompt,
            )
            if task_doc:
                conversation_status = "analyzing"
                task_progress = build_task_progress(task_doc)

        return _build_resolution_response(
            resolution_id=resolution_id,
            result=result,
            conversation_status=conversation_status,
            messages=[user_message, assistant_message],
            analysis_prompt=analysis_prompt,
            accepted=None,
            task_progress=task_progress,
        )

    def confirm_resolution(
        self,
        *,
        user_id: str,
        conversation_id: str,
        payload: ResolutionConfirmRequest,
    ) -> ResolutionResponse:
        conversation = self._get_conversation(user_id=user_id, conversation_id=conversation_id)
        pending = _parse_pending_snapshot(conversation.get("pendingResolution"))
        if not pending or pending.resolutionId != payload.resolutionId:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resolution state is stale or unavailable",
            )

        if payload.action == "restart":
            assistant_reply = "好的，请重新输入你想分析的具体股票名称或 ticker。"
            assistant_message = self.message_repo.create(
                conversation_id=conversation_id,
                role="assistant",
                message_type=MessageType.TICKER_RESOLUTION,
                content={
                    "text": assistant_reply,
                    "status": "collect_more",
                    "resolutionId": payload.resolutionId,
                    "candidates": [],
                },
            )
            self.state_machine.transition(
                conversation_id=conversation_id,
                user_id=user_id,
                to_status="collecting_inputs",
                pending_resolution=None,
                confirmed_stock=None,
                confirmed_analysis_prompt=None,
            )
            return ResolutionResponse(
                resolutionId=payload.resolutionId,
                accepted=False,
                status="collect_more",
                promptMessage=assistant_reply,
                conversationStatus="collecting_inputs",
                messages=[build_message(assistant_message)],
                analysisPrompt=None,
            )

        selected_stock = self._resolve_selected_stock(pending=pending, payload=payload)
        assistant_reply = f"已为你确认分析标的是 {selected_stock.name}（{selected_stock.ticker}）。"
        assistant_message = self.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            message_type=MessageType.TICKER_RESOLUTION,
            content={
                "text": assistant_reply,
                "status": "resolved",
                "resolutionId": payload.resolutionId,
                "ticker": selected_stock.ticker,
                "name": selected_stock.name,
                "candidates": [],
                "analysisPrompt": pending.analysisPrompt,
                "focusPoints": pending.focusPoints,
            },
        )
        self.state_machine.transition(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status="ready_to_analyze",
            pending_resolution=None,
            confirmed_stock=selected_stock.model_dump(),
            confirmed_analysis_prompt=pending.analysisPrompt,
        )
        logger.info(
            "resolution_confirmed conversation_id=%s resolution_id=%s ticker=%s",
            conversation_id,
            payload.resolutionId,
            selected_stock.ticker,
        )

        conversation_status = "ready_to_analyze"
        task_progress = None
        task_doc = self._try_launch_analysis(
            user_id=user_id,
            conversation_id=conversation_id,
            ticker=selected_stock.ticker,
            prompt=pending.analysisPrompt,
        )
        if task_doc:
            conversation_status = "analyzing"
            task_progress = build_task_progress(task_doc)

        return ResolutionResponse(
            resolutionId=payload.resolutionId,
            accepted=True,
            status="resolved",
            ticker=selected_stock.ticker,
            name=selected_stock.name,
            candidates=[],
            promptMessage=assistant_reply,
            conversationStatus=conversation_status,
            messages=[build_message(assistant_message)],
            analysisPrompt=pending.analysisPrompt,
            focusPoints=list(pending.focusPoints),
            taskProgress=task_progress,
        )

    def _try_launch_analysis(
        self,
        *,
        user_id: str,
        conversation_id: str,
        ticker: str,
        prompt: str,
    ) -> dict | None:
        """
        尝试立即启动分析任务，返回任务文档（含进度字段）。
        失败时仅记录日志，返回 None，不阻断 resolution 响应。
        """
        active_task = self.task_repo.get_active_for_user(user_id)
        if active_task:
            logger.warning(
                "auto_launch_skipped reason=active_task_exists user_id=%s conversation_id=%s",
                user_id, conversation_id,
            )
            return None
        if not self.queue.acquire_user_lock(user_id):
            logger.warning(
                "auto_launch_skipped reason=lock_unavailable user_id=%s conversation_id=%s",
                user_id, conversation_id,
            )
            return None
        trade_date = _TODAY().strftime("%Y%m%d")
        try:
            task_doc = self.analysis_service.launch_analysis(
                user_id=user_id,
                conversation_id=conversation_id,
                ticker=ticker,
                trade_date=trade_date,
                prompt=prompt,
            )
            logger.info(
                "auto_launch_success conversation_id=%s ticker=%s task_id=%s",
                conversation_id, ticker, task_doc["taskId"],
            )
            return task_doc
        except Exception as exc:
            logger.exception(
                "auto_launch_failed conversation_id=%s ticker=%s error=%s",
                conversation_id, ticker, exc,
            )
            return None

    def _get_conversation(self, *, user_id: str, conversation_id: str) -> dict:
        conversation = self.conversation_repo.get_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation

    def _ensure_resolution_allowed(self, conversation: dict) -> None:
        conv_status = conversation.get("status")
        if conv_status == "analyzing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is still running for this conversation",
            )
        if conv_status in ("report_ready", "report_explaining"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation has a completed report; use post_message to continue",
            )

    def _resolve_selected_stock(
        self,
        *,
        pending: PendingResolutionSnapshot,
        payload: ResolutionConfirmRequest,
    ) -> ResolutionCandidate:
        candidates = pending.candidates
        if payload.action == "confirm":
            if pending.status != "need_confirm" or not candidates:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resolution is not confirmable")
            ticker = candidates[0].ticker
        elif payload.action == "select":
            if pending.status != "need_disambiguation":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resolution is not selectable")
            ticker = (payload.ticker or "").strip().upper()
            if not ticker or all(item.ticker != ticker for item in candidates):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticker is not in candidate list")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported resolution action")

        try:
            stock = self.stock_lookup_gateway.get_stock_profile(ticker=ticker)
        except StockLookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stock profile service is unavailable",
            ) from exc
        if stock is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock profile not found")
        return stock


def _build_resolution_response(
    *,
    resolution_id: str,
    result: AgentResolutionResult,
    conversation_status: str,
    messages: list[dict],
    analysis_prompt: str,
    accepted: bool | None,
    task_progress=None,
) -> ResolutionResponse:
    return ResolutionResponse(
        resolutionId=resolution_id,
        accepted=accepted,
        status=result.status,
        ticker=result.stock.ticker if result.stock else None,
        name=result.stock.name if result.stock else None,
        candidates=result.candidates,
        promptMessage=result.assistantReply,
        conversationStatus=conversation_status,
        messages=[build_message(message) for message in messages],
        analysisPrompt=analysis_prompt,
        focusPoints=result.focusPoints,
        taskProgress=task_progress,
    )


def _build_resolution_message_content(
    *,
    resolution_id: str,
    result: AgentResolutionResult,
    analysis_prompt: str,
) -> dict:
    return {
        "text": result.assistantReply,
        "status": result.status,
        "resolutionId": resolution_id,
        "ticker": result.stock.ticker if result.stock else None,
        "name": result.stock.name if result.stock else None,
        "candidates": [candidate.model_dump() for candidate in result.candidates],
        "analysisPrompt": analysis_prompt,
        "focusPoints": result.focusPoints,
    }


def _build_pending_resolution(
    *,
    resolution_id: str,
    round_number: int,
    result: AgentResolutionResult,
    original_message: str,
    analysis_prompt: str,
) -> PendingResolutionSnapshot | None:
    if result.status in {"resolved", "failed", "unsupported"}:
        return None

    candidates = result.candidates or ([result.stock] if result.stock else [])
    return PendingResolutionSnapshot(
        resolutionId=resolution_id,
        status=result.status,
        round=round_number,
        originalMessage=original_message,
        analysisPrompt=analysis_prompt,
        assistantReply=result.assistantReply,
        candidates=[candidate for candidate in candidates if candidate is not None],
        resolvedStock=result.stock,
        focusPoints=result.focusPoints,
        updatedAt=datetime.now(timezone.utc),
    )


def _parse_pending_snapshot(pending: dict | None) -> PendingResolutionSnapshot | None:
    if not pending:
        return None
    return PendingResolutionSnapshot.model_validate(pending)


def _build_prior_summary(pending: PendingResolutionSnapshot | None) -> str:
    if pending is None:
        return ""
    candidate_labels = ", ".join(f"{item.name}({item.ticker})" for item in pending.candidates[:3]) or "无"
    return (
        f"上一轮状态={pending.status}；"
        f"上一轮原始输入={pending.originalMessage}；"
        f"上一轮候选={candidate_labels}；"
        f"上一轮关注点={','.join(pending.focusPoints) or '无'}。"
    )


def _compose_analysis_prompt(*, existing_pending: PendingResolutionSnapshot | None, message: str) -> str:
    if not existing_pending:
        return message

    # 上一轮 collect_more 说明没有识别出有效标的，历史 prompt 是噪音，不累积
    if existing_pending.status == "collect_more":
        return message

    current_prompt = (existing_pending.analysisPrompt or "").strip()
    if not current_prompt:
        return message
    if _is_reset_message(message):
        return message
    return f"{current_prompt}\n{message}".strip()


def _is_reset_message(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in ("改成", "换成", "重新", "不要", "不是"))
