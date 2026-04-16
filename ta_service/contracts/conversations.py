from __future__ import annotations

from ta_service.models.conversation import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    TaskProgress,
    TaskProgressItem,
)
from ta_service.runtime.status_mapper import (
    normalize_mobile_status,
    resolve_display_state,
    resolve_elapsed_time,
    resolve_node_message,
    resolve_remaining_time,
    resolve_stage_message,
)
from ta_service.teams import get_team_spec


def _build_task_items(task_doc: dict) -> list[TaskProgressItem]:
    team_spec = get_team_spec(task_doc.get("teamId"))
    selected_analysts = set(task_doc.get("selectedAnalysts") or [])
    snapshot = task_doc.get("stageSnapshot") or {}
    timeline = task_doc.get("stageTimeline") or {}
    items: list[TaskProgressItem] = []

    for stage in team_spec.stage_contract.stages:
        if stage.stage_group == "analysts":
            analyst_key = stage.stage_id.split(".", 1)[1]
            if selected_analysts and analyst_key not in selected_analysts:
                continue
        timeline_item = timeline.get(stage.stage_id) or {}
        status = (
            snapshot.get(stage.stage_id)
            or timeline_item.get("status")
            or ("completed" if normalize_mobile_status(task_doc.get("status", "")) == "completed" else "pending")
        )
        items.append(
            TaskProgressItem(
                stageId=stage.stage_id,
                label=resolve_stage_message(stage.stage_id) or stage.label,
                status=status,
                startedAt=timeline_item.get("startedAt"),
                completedAt=timeline_item.get("completedAt"),
            )
        )
    return items


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
        stageSnapshot=task_doc.get("stageSnapshot") or None,
        displayState=resolve_display_state(task_doc),
        currentStep=current_step,
        message=message,
        elapsedTime=elapsed,
        remainingTime=resolve_remaining_time(task_doc, elapsed),
        tasks=_build_task_items(task_doc),
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
