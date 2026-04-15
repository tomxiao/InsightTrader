import type {
  ConversationDetail,
  ConversationSummary,
  CreateConversationRequest,
  PostConversationMessageRequest,
  PostConversationMessageResponse
} from '@/types/conversation'
import type { ResolutionConfirmRequest, ResolutionRequest, ResolutionResponse } from '@/types/resolution'

import { request } from './request'

const followupRequestTimeoutMs = 240000

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
      .post<PostConversationMessageResponse>(`/conversations/${conversationId}/messages`, payload, {
        timeout: followupRequestTimeoutMs
      })
      .then(response => response.data)
  },
  resolve(conversationId: string, payload: ResolutionRequest) {
    return request
      .post<ResolutionResponse>(`/conversations/${conversationId}/resolution`, payload, {
        timeout: followupRequestTimeoutMs
      })
      .then(response => response.data)
  },
  confirmResolution(conversationId: string, payload: ResolutionConfirmRequest) {
    return request
      .post<ResolutionResponse>(`/conversations/${conversationId}/resolution/confirm`, payload, {
        timeout: followupRequestTimeoutMs
      })
      .then(response => response.data)
  },
  deleteConversation(conversationId: string) {
    return request.delete(`/conversations/${conversationId}`).then(response => response.data)
  }
}
