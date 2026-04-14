from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ta_service.api.deps import get_conversation_service, get_current_user, get_resolution_service
from ta_service.models.auth import MobileUser
from ta_service.models.conversation import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    PostConversationMessageRequest,
    PostConversationMessageResponse,
)
from ta_service.models.resolution import (
    ResolutionConfirmRequest,
    ResolutionRequest,
    ResolutionResponse,
)
from ta_service.services.conversation_service import ConversationService
from ta_service.services.resolution_service import ResolutionService

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


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: MobileUser = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    conversation_service.delete_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


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


@router.post("/{conversation_id}/resolution", response_model=ResolutionResponse)
def resolve_conversation_message(
    conversation_id: str,
    payload: ResolutionRequest,
    current_user: MobileUser = Depends(get_current_user),
    resolution_service: ResolutionService = Depends(get_resolution_service),
) -> ResolutionResponse:
    return resolution_service.resolve_message(
        user_id=current_user.id,
        conversation_id=conversation_id,
        message=payload.message,
    )


@router.post("/{conversation_id}/resolution/confirm", response_model=ResolutionResponse)
def confirm_conversation_resolution(
    conversation_id: str,
    payload: ResolutionConfirmRequest,
    current_user: MobileUser = Depends(get_current_user),
    resolution_service: ResolutionService = Depends(get_resolution_service),
) -> ResolutionResponse:
    return resolution_service.confirm_resolution(
        user_id=current_user.id,
        conversation_id=conversation_id,
        payload=payload,
    )
