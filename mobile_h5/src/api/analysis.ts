import { request } from './request'

export const analysisApi = {
  getTaskStatus(taskId: string) {
    return request.get(`/analysis/tasks/${taskId}/status`)
  }
}
