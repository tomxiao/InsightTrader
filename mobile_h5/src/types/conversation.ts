import type {
  MessageType,
  TaskStatusContent,
  ErrorContent,
  SummaryCardContent,
  TickerResolutionContent,
} from '@/types/messageTypes'

export type { MessageType }

export type ConversationStatus =
  | 'idle'
  | 'collecting_inputs'
  | 'ready_to_analyze'
  | 'analyzing'
  | 'report_ready'
  | 'report_explaining'
  | 'failed'

/** @deprecated 请使用 MessageType（来自 @/types/messageTypes） */
export type ConversationMessageType = MessageType

export interface TaskProgress {
  status?: string
  stageId?: string
  nodeId?: string
  displayState?: 'pending' | 'active' | 'stalled' | 'done' | 'failed' | string
  currentStep?: string
  message?: string
  elapsedTime?: number
  remainingTime?: number
}

export interface ConversationSummary {
  id: string
  title: string
  status: ConversationStatus
  updatedAt: string
}

export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  messageType: MessageType
  content:
    | string
    | TaskStatusContent
    | ErrorContent
    | SummaryCardContent
    | TickerResolutionContent
  createdAt: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
  taskProgress?: TaskProgress | null
}

export interface CreateConversationRequest {
  title?: string
}

export interface PostConversationMessageRequest {
  message: string
}

export interface PostConversationMessageResponse {
  messages: ConversationMessage[]
}
