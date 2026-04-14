import { onBeforeUnmount, onMounted, watch } from 'vue'
import { conversationsApi } from '@api/conversations'
import { useConversationStore } from '@stores/conversation'

/**
 * 管理当前会话的状态轮询。
 *
 * 职责：
 * - 会话状态为 analyzing 时每 3 秒拉取一次 GET /conversations/{id}
 * - 后端返回的 ConversationDetail 整体覆盖 store，包含 taskProgress 进度信息
 * - 状态变为非 analyzing 时自动停止轮询
 * - 页面切入后台（visibilitychange hidden）时暂停，切回前台时恢复
 * - 组件卸载时清理定时器和事件监听
 */
export function useConversationPolling(getConversationId: () => string) {
  const conversationStore = useConversationStore()

  let timer: number | null = null
  let activeRunId = 0
  let inFlight = false

  const stopPolling = () => {
    activeRunId += 1
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  const poll = async (runId: number) => {
    if (inFlight) {
      return
    }

    const id = getConversationId()
    if (!id) return

    inFlight = true
    try {
      const detail = await conversationsApi.getConversation(id)
      if (runId === activeRunId && detail.id === getConversationId()) {
        conversationStore.setCurrentConversation(detail)
      }
    } catch {
      // 轮询失败静默处理，下次间隔继续尝试
    } finally {
      inFlight = false
    }
  }

  const startPolling = () => {
    stopPolling()
    const runId = activeRunId
    const id = getConversationId()
    if (!id) return
    void poll(runId)
    timer = window.setInterval(() => {
      void poll(runId)
    }, 3000)
  }

  const onVisibilityChange = () => {
    if (document.hidden) {
      stopPolling()
    } else if (conversationStore.currentConversation.status === 'analyzing') {
      startPolling()
    }
  }

  watch(
    () => conversationStore.currentConversation.status,
    status => {
      if (status === 'analyzing') {
        startPolling()
      } else {
        stopPolling()
      }
    },
    { immediate: true }
  )

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
    stopPolling()
  })

  return { startPolling, stopPolling }
}
