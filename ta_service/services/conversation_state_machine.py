from __future__ import annotations

import logging

from ta_service.repos.conversations import ConversationRepository

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "idle":               {"collecting_inputs", "ready_to_analyze", "analyzing"},
    "collecting_inputs":  {"collecting_inputs", "ready_to_analyze", "analyzing"},
    "ready_to_analyze":   {"collecting_inputs", "analyzing"},
    "analyzing":          {"report_ready", "failed"},
    "report_ready":       {"report_explaining"},
    "report_explaining":  {"report_explaining", "idle"},
    "failed":             {"collecting_inputs", "idle"},
}

_SENTINEL = object()


class InvalidStateTransitionError(Exception):
    """试图执行不合法的会话状态流转时抛出。"""


class ConversationStateMachine:
    """
    会话状态机：所有合法的会话状态流转均通过此类完成。

    Repository 层负责数据读写，本类负责业务合法性校验与统一持久化入口。
    外部代码不应直接调用 ConversationRepository 写入 status 字段。
    """

    def __init__(self, *, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    def transition(
        self,
        *,
        conversation_id: str,
        user_id: str,
        to_status: str,
        title: str | None = None,
        task_id: object = _SENTINEL,
        report_id: object = _SENTINEL,
        pending_resolution: object = _SENTINEL,
        confirmed_stock: object = _SENTINEL,
        confirmed_analysis_prompt: object = _SENTINEL,
    ) -> None:
        """
        执行一次合法的会话状态流转并持久化。

        会先从数据库读取当前状态进行合法性校验，若流转不合法则抛出
        InvalidStateTransitionError。
        """
        document = self.conversation_repo.get_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not document:
            raise InvalidStateTransitionError(
                f"conversation {conversation_id} not found for user {user_id}"
            )

        from_status = document.get("status", "idle")
        self._check_transition(from_status=from_status, to_status=to_status, conversation_id=conversation_id)

        self._persist(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status=to_status,
            title=title,
            task_id=task_id,
            report_id=report_id,
            pending_resolution=pending_resolution,
            confirmed_stock=confirmed_stock,
            confirmed_analysis_prompt=confirmed_analysis_prompt,
        )
        logger.info(
            "conversation_state_transition conversation_id=%s %s -> %s",
            conversation_id,
            from_status,
            to_status,
        )

    def transition_unchecked(
        self,
        *,
        conversation_id: str,
        user_id: str,
        to_status: str,
        task_id: object = _SENTINEL,
        report_id: object = _SENTINEL,
    ) -> None:
        """
        跳过合法性检查的状态流转，仅供 Worker 等可信内部路径使用。

        Worker 进程独立运行，读取当前状态再校验会增加一次数据库查询，且
        Worker 只写终态（report_ready / failed），风险可控。
        """
        self._persist(
            conversation_id=conversation_id,
            user_id=user_id,
            to_status=to_status,
            task_id=task_id,
            report_id=report_id,
        )
        logger.info(
            "conversation_state_transition_unchecked conversation_id=%s -> %s",
            conversation_id,
            to_status,
        )

    @staticmethod
    def _check_transition(*, from_status: str, to_status: str, conversation_id: str) -> None:
        allowed = _VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidStateTransitionError(
                f"conversation {conversation_id}: "
                f"transition '{from_status}' -> '{to_status}' is not allowed. "
                f"Allowed targets from '{from_status}': {sorted(allowed)}"
            )

    def _persist(
        self,
        *,
        conversation_id: str,
        user_id: str,
        to_status: str,
        title: str | None = None,
        task_id: object = _SENTINEL,
        report_id: object = _SENTINEL,
        pending_resolution: object = _SENTINEL,
        confirmed_stock: object = _SENTINEL,
        confirmed_analysis_prompt: object = _SENTINEL,
    ) -> None:
        self.conversation_repo.update_conversation_state(
            conversation_id=conversation_id,
            user_id=user_id,
            status=to_status,
            title=title,
            task_id=None if task_id is _SENTINEL else task_id,
            set_task_id=(task_id is not _SENTINEL),
            report_id=None if report_id is _SENTINEL else report_id,
            set_report_id=(report_id is not _SENTINEL),
            pending_resolution=None if pending_resolution is _SENTINEL else pending_resolution,
            set_pending_resolution=(pending_resolution is not _SENTINEL),
            confirmed_stock=None if confirmed_stock is _SENTINEL else confirmed_stock,
            set_confirmed_stock=(confirmed_stock is not _SENTINEL),
            confirmed_analysis_prompt=None if confirmed_analysis_prompt is _SENTINEL else confirmed_analysis_prompt,
            set_confirmed_analysis_prompt=(confirmed_analysis_prompt is not _SENTINEL),
        )
