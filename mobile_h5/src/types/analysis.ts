export type MobileTaskStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed'

export interface AnalysisTaskSummary {
  taskId: string
  status: MobileTaskStatus
  symbol?: string
  currentStep?: string
  message?: string
  elapsedTime?: number
  remainingTime?: number
  reportId?: string
}

export interface CreateAnalysisTaskRequest {
  conversationId: string
  ticker: string
  tradeDate: string
  prompt?: string
  selectedAnalysts?: string[]
}
