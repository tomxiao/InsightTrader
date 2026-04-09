from __future__ import annotations

from ta_service.contracts.conversations import (
    build_conversation_detail,
    build_conversation_summary,
)
from ta_service.models.conversation import ConversationDetail, ConversationSummary
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository


class ConversationService:
    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    def create_conversation(self, *, user_id: str, title: str | None) -> ConversationSummary:
        document = self.conversation_repo.create(user_id=user_id, title=title or "新会话")
        return build_conversation_summary(document)

    def list_conversations(self, *, user_id: str) -> list[ConversationSummary]:
        return [
            build_conversation_summary(document)
            for document in self.conversation_repo.list_for_user(user_id)
        ]

    def get_conversation(self, *, user_id: str, conversation_id: str) -> ConversationDetail | None:
        document = self.conversation_repo.get_for_user(conversation_id=conversation_id, user_id=user_id)
        if not document:
            return None
        messages = self.message_repo.list_for_conversation(conversation_id)
        return build_conversation_detail(document, messages)
