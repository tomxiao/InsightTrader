from __future__ import annotations

from ta_service.models.conversation import ConversationDetail, ConversationMessage, ConversationSummary, TaskProgress
from ta_service.runtime.status_mapper import resolve_elapsed_time, resolve_remaining_time, resolve_stage_message


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
    current_step = task_doc.get("currentStep") or resolve_stage_message(task_doc.get("stageId"))
    message = task_doc.get("message") or current_step
    return TaskProgress(
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
    if summary.status == "analyzing" and task_doc:
        task_progress = build_task_progress(task_doc)
    return ConversationDetail(
        **summary.model_dump(),
        messages=[build_message(message) for message in messages],
        taskProgress=task_progress,
    )
