from __future__ import annotations

from ta_service.models.conversation import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    TaskProgress,
)
from ta_service.runtime.status_mapper import (
    normalize_mobile_status,
    resolve_display_state,
    resolve_elapsed_time,
    resolve_node_message,
    resolve_remaining_time,
    resolve_stage_message,
)


def build_message(document: dict) -> ConversationMessage:
    return ConversationMessage(
        id=document["id"],
        role=document["role"],
        messageType=document.get("messageType", "text"),
        content=document.get("content", ""),
        createdAt=document["createdAt"],
    )


def build_conversation_summary(document: dict) -> ConversationSummary:
    return ConversationSummary(
        id=document["id"],
        title=document["title"],
        status=document["status"],
        updatedAt=document["updatedAt"],
    )


def build_task_progress(task_doc: dict) -> TaskProgress:
    elapsed = resolve_elapsed_time(task_doc)
    stage_id = task_doc.get("stageId")
    node_id = task_doc.get("nodeId")
    current_step = (
        task_doc.get("currentStep")
        or resolve_node_message(node_id)
        or resolve_stage_message(stage_id)
    )
    message = task_doc.get("message") or resolve_node_message(node_id) or current_step
    return TaskProgress(
        status=normalize_mobile_status(task_doc.get("status", "")),
        stageId=stage_id,
        nodeId=node_id,
        displayState=resolve_display_state(task_doc),
        currentStep=current_step,
        message=message,
        elapsedTime=elapsed,
        remainingTime=resolve_remaining_time(task_doc, elapsed),
    )


def build_conversation_detail(
    document: dict,
    messages: list[dict],
    task_doc: dict | None = None,
) -> ConversationDetail:
    summary = build_conversation_summary(document)
    task_progress: TaskProgress | None = None
    if summary.status in {"analyzing", "report_ready", "report_explaining", "failed"} and task_doc:
        task_progress = build_task_progress(task_doc)
    return ConversationDetail(
        **summary.model_dump(),
        messages=[build_message(message) for message in messages],
        taskProgress=task_progress,
    )
