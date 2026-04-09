export type ConversationStatus =
  | 'idle'
  | 'collecting_inputs'
  | 'ready_to_analyze'
  | 'analyzing'
  | 'report_ready'
  | 'report_explaining'
  | 'failed'

export type ConversationMessageType =
  | 'text'
  | 'task_status'
  | 'summary_card'
  | 'report_card'
  | 'error'

export interface ConversationSummary {
  id: string
  title: string
  status: ConversationStatus
  updatedAt: string
  lastReportId?: string | null
  currentTaskId?: string | null
}

export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  messageType: ConversationMessageType
  content:
    | string
    | {
        text?: string
        reportId?: string
        title?: string
      }
  createdAt: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}

export interface CreateConversationRequest {
  title?: string
}

export interface PostConversationMessageRequest {
  message: string
}

export interface PostConversationMessageResponse {
  messages: ConversationMessage[]
  reportId?: string | null
}
