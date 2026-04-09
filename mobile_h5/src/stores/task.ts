import { defineStore } from 'pinia'
import type { AnalysisTaskSummary, MobileTaskStatus } from '@/types/analysis'

const idleTask: AnalysisTaskSummary = {
  taskId: '',
  status: 'idle'
}

export const useTaskStore = defineStore('mobile-task', {
  state: () => ({
    currentTask: { ...idleTask },
    draftMessage: ''
  }),
  getters: {
    hasRunningTask: state =>
      ['pending', 'running'].includes(state.currentTask.status as MobileTaskStatus)
  },
  actions: {
    setTask(task: AnalysisTaskSummary) {
      this.currentTask = task
    },
    clearTask() {
      this.currentTask = { ...idleTask }
    },
    setDraftMessage(message: string) {
      this.draftMessage = message
    }
  }
})
