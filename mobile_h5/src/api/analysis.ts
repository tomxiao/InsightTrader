import type { AnalysisTaskSummary, CreateAnalysisTaskRequest } from '@/types/analysis'
import { request } from './request'

export const analysisApi = {
  createTask(payload: CreateAnalysisTaskRequest) {
    return request.post<AnalysisTaskSummary>('/analysis/tasks', payload).then(response => response.data)
  },
  getTaskStatus(taskId: string) {
    return request.get<AnalysisTaskSummary>(`/analysis/tasks/${taskId}/status`).then(response => response.data)
  }
}
