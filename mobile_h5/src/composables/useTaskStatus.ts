import { storeToRefs } from 'pinia'
import { useTaskStore } from '@stores/task'

export const useTaskStatus = () => {
  const taskStore = useTaskStore()
  const { currentTask, hasRunningTask, draftMessage } = storeToRefs(taskStore)

  return {
    currentTask,
    hasRunningTask,
    draftMessage,
    setTask: taskStore.setTask,
    clearTask: taskStore.clearTask,
    setDraftMessage: taskStore.setDraftMessage
  }
}
