import type {
  ConversationDetail,
  ConversationSummary,
  CreateConversationRequest,
  PostConversationMessageRequest,
  PostConversationMessageResponse
} from '@/types/conversation'

import { request } from './request'

export const conversationsApi = {
  createConversation(payload: CreateConversationRequest) {
    return request.post<ConversationSummary>('/conversations', payload).then(response => response.data)
  },
  listConversations() {
    return request.get<ConversationSummary[]>('/conversations').then(response => response.data)
  },
  getConversation(id: string) {
    return request.get<ConversationDetail>(`/conversations/${id}`).then(response => response.data)
  },
  postMessage(conversationId: string, payload: PostConversationMessageRequest) {
    return request
      .post<PostConversationMessageResponse>(`/conversations/${conversationId}/messages`, payload)
      .then(response => response.data)
  }
}
