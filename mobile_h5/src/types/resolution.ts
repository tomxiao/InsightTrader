import type { ConversationMessage, ConversationStatus, TaskProgress } from '@/types/conversation'
import type {
  ResolutionCandidate,
  ResolutionStatus,
  TickerResolutionContent,
} from '@/types/messageTypes'

export type { ResolutionCandidate, ResolutionStatus }

export type ResolutionAction = 'confirm' | 'select' | 'restart'

/** @deprecated 请使用 TickerResolutionContent（来自 @/types/messageTypes） */
export type ResolutionMessageContent = TickerResolutionContent

export interface ResolutionRequest {
  message: string
}

export interface ResolutionConfirmRequest {
  action: ResolutionAction
  resolutionId: string
  ticker?: string
}

export interface ResolutionResponse {
  resolutionId?: string | null
  accepted?: boolean | null
  status: ResolutionStatus
  ticker?: string | null
  name?: string | null
  candidates: ResolutionCandidate[]
  promptMessage: string
  conversationStatus: ConversationStatus
  messages: ConversationMessage[]
  analysisPrompt?: string | null
  focusPoints?: string[]
  taskProgress?: TaskProgress | null
}
