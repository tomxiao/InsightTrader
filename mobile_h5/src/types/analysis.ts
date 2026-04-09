export type MobileTaskStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed'

export interface AnalysisTaskSummary {
  taskId: string
  status: MobileTaskStatus
  symbol?: string
  currentStep?: string
  message?: string
  elapsedTime?: number
  remainingTime?: number
}
