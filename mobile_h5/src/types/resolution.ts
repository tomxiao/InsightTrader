import type { ConversationMessage, ConversationStatus } from '@/types/conversation'

export type ResolutionStatus =
  | 'collect_more'
  | 'need_confirm'
  | 'need_disambiguation'
  | 'resolved'
  | 'unsupported'
  | 'failed'

export type ResolutionAction = 'confirm' | 'select' | 'restart'

export interface ResolutionCandidate {
  ticker: string
  name: string
  market?: string | null
  exchange?: string | null
  aliases?: string[]
  score?: number | null
  assetType?: string
  isActive?: boolean | null
}

export interface ResolutionMessageContent {
  text?: string
  status?: ResolutionStatus
  resolutionId?: string
  ticker?: string | null
  name?: string | null
  candidates?: ResolutionCandidate[]
  analysisPrompt?: string
  focusPoints?: string[]
}

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
}
