import { computed } from 'vue'
import { useTaskStore } from '@stores/task'

export const useDraft = () => {
  const taskStore = useTaskStore()

  return {
    draftMessage: computed(() => taskStore.draftMessage),
    setDraftMessage: taskStore.setDraftMessage
  }
}
