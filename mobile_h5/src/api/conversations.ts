import type {
  ConversationDetail,
  ConversationMessage,
  ConversationSummary,
  CreateConversationRequest,
  PostConversationMessageRequest,
  PostConversationMessageResponse
} from '@/types/conversation'
import type { ResolutionConfirmRequest, ResolutionRequest, ResolutionResponse } from '@/types/resolution'

import { env } from '@utils/env'
import { useAuthStore } from '@stores/auth'
import { request } from './request'

const followupRequestTimeoutMs = 240000

export type StreamMessageEvent =
  | { event: 'started'; userMessage: ConversationMessage }
  | {
      event: 'routing'
      routing_intent?: string | null
      routing_primary_section?: string | null
      routing_fallback_sections?: string[]
      routing_reason?: string | null
      llm_router_ms?: number | null
    }
  | { event: 'delta'; text: string }
  | { event: 'completed'; assistantMessage: ConversationMessage }
  | { event: 'error'; message: string; status_code?: number }

type StreamHandlers = {
  onEvent: (event: StreamMessageEvent) => void
}

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
  async streamPostMessage(
    conversationId: string,
    payload: PostConversationMessageRequest,
    handlers: StreamHandlers
  ) {
    const authStore = useAuthStore()
    const response = await fetch(`${env.apiBaseUrl}/conversations/${conversationId}/messages/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}),
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok || !response.body) {
      let message = '流式回复失败，请稍后再试'
      try {
        const data = await response.json()
        if (typeof data?.detail === 'string') {
          message = data.detail
        }
      } catch {
        // ignore JSON parse errors
      }
      throw new Error(message)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let boundary = buffer.indexOf('\n\n')
      while (boundary >= 0) {
        const rawEvent = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const parsed = parseSseEvent(rawEvent)
        if (parsed) {
          handlers.onEvent(parsed)
        }
        boundary = buffer.indexOf('\n\n')
      }
    }
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

function parseSseEvent(rawEvent: string): StreamMessageEvent | null {
  const lines = rawEvent.split('\n')
  let event = 'message'
  const dataLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
      continue
    }
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }

  if (!dataLines.length) return null
  try {
    return { event, ...JSON.parse(dataLines.join('\n')) } as StreamMessageEvent
  } catch {
    return null
  }
}
