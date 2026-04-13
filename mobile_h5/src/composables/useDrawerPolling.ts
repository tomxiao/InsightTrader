import { onBeforeUnmount, watch } from 'vue'
import { conversationsApi } from '@api/conversations'
import { useConversationStore } from '@stores/conversation'

/**
 * 管理抽屉（会话列表）的状态轮询。
 *
 * 职责：
 * - 抽屉打开时，立即刷新一次会话列表，随后每 3 秒轮询一次
 * - 抽屉关闭时自动停止轮询
 * - 组件卸载时清理定时器
 */
export function useDrawerPolling() {
  const conversationStore = useConversationStore()

  let timer: number | null = null

  const stopPolling = () => {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  const poll = async () => {
    try {
      const conversations = await conversationsApi.listConversations()
      conversationStore.setConversations(conversations)
    } catch {
      // 静默失败：抽屉列表属于低优先级刷新，不打断用户
    }
  }

  const startPolling = async () => {
    stopPolling()
    await poll()
    timer = window.setInterval(poll, 3000)
  }

  watch(
    () => conversationStore.isDrawerOpen,
    open => {
      if (open) {
        startPolling()
      } else {
        stopPolling()
      }
    }
  )

  onBeforeUnmount(stopPolling)
}
