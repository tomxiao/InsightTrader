import { defineStore } from 'pinia'
import type { AnalysisTaskSummary, MobileTaskStatus } from '@/types/analysis'
import { storage } from '@utils/storage'

const TASK_KEY = 'frontend_mobile_current_task'
const DRAFT_KEY = 'frontend_mobile_task_draft'

const idleTask: AnalysisTaskSummary = {
  taskId: '',
  status: 'idle'
}

export const useTaskStore = defineStore('mobile-task', {
  state: () => ({
    currentTask: storage.get<AnalysisTaskSummary>(TASK_KEY, { ...idleTask }),
    draftMessage: storage.get<string>(DRAFT_KEY, '')
  }),
  getters: {
    hasRunningTask: state =>
      ['pending', 'running'].includes(state.currentTask.status as MobileTaskStatus)
  },
  actions: {
    setTask(task: AnalysisTaskSummary) {
      this.currentTask = {
        ...idleTask,
        ...task
      }
      storage.set(TASK_KEY, this.currentTask)
    },
    clearTask() {
      this.currentTask = { ...idleTask }
      storage.remove(TASK_KEY)
    },
    setDraftMessage(message: string) {
      this.draftMessage = message
      if (message) {
        storage.set(DRAFT_KEY, message)
      } else {
        storage.remove(DRAFT_KEY)
      }
    }
  }
})
