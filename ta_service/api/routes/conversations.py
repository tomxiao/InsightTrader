from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ta_service.api.deps import get_conversation_service, get_current_user
from ta_service.models.auth import MobileUser
from ta_service.models.conversation import (
    ConversationDetail,
    PostConversationMessageRequest,
    PostConversationMessageResponse,
    ConversationSummary,
    CreateConversationRequest,
)
from ta_service.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: CreateConversationRequest,
    current_user: MobileUser = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationSummary:
    return conversation_service.create_conversation(user_id=current_user.id, title=payload.title)


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    current_user: MobileUser = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationSummary]:
    return conversation_service.list_conversations(user_id=current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    current_user: MobileUser = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    conversation = conversation_service.get_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


@router.post("/{conversation_id}/messages", response_model=PostConversationMessageResponse)
def post_conversation_message(
    conversation_id: str,
    payload: PostConversationMessageRequest,
    current_user: MobileUser = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> PostConversationMessageResponse:
    return conversation_service.post_message(
        user_id=current_user.id,
        conversation_id=conversation_id,
        message=payload.message,
    )
