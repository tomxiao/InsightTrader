from __future__ import annotations

from ta_service.models.conversation import ConversationDetail, ConversationMessage, ConversationSummary


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
        lastReportId=document.get("lastReportId"),
        currentTaskId=document.get("currentTaskId"),
    )


def build_conversation_detail(document: dict, messages: list[dict]) -> ConversationDetail:
    return ConversationDetail(
        **build_conversation_summary(document).model_dump(),
        messages=[build_message(message) for message in messages],
    )
