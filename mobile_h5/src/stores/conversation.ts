import { defineStore } from 'pinia'
import type { ConversationDetail, ConversationMessage, ConversationSummary } from '@/types/conversation'
import { storage } from '@utils/storage'

const CURRENT_CONVERSATION_KEY = 'frontend_mobile_current_conversation'
const CONVERSATION_LIST_KEY = 'frontend_mobile_conversation_list'
const DRAWER_KEY = 'frontend_mobile_drawer_open'

const emptyConversation: ConversationDetail = {
  id: '',
  title: '新会话',
  status: 'idle',
  updatedAt: '',
  lastReportId: null,
  taskProgress: null,
  messages: []
}

export const useConversationStore = defineStore('mobile-conversation', {
  state: () => ({
    conversations: storage.get<ConversationSummary[]>(CONVERSATION_LIST_KEY, []),
    currentConversation: storage.get<ConversationDetail>(CURRENT_CONVERSATION_KEY, { ...emptyConversation }),
    isDrawerOpen: storage.get<boolean>(DRAWER_KEY, false),
    isLoading: false
  }),
  getters: {
    currentConversationId: state => state.currentConversation.id,
    currentTitle: state => state.currentConversation.title || '新会话',
    currentMessages: state => state.currentConversation.messages
  },
  actions: {
    setConversations(items: ConversationSummary[]) {
      this.conversations = items
      storage.set(CONVERSATION_LIST_KEY, items)
    },
    upsertConversation(summary: ConversationSummary) {
      const index = this.conversations.findIndex(item => item.id === summary.id)
      if (index >= 0) {
        this.conversations.splice(index, 1, summary)
      } else {
        this.conversations.unshift(summary)
      }
      this.conversations.sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
      storage.set(CONVERSATION_LIST_KEY, this.conversations)
    },
    setCurrentConversation(detail: ConversationDetail) {
      this.currentConversation = detail
      storage.set(CURRENT_CONVERSATION_KEY, detail)
      this.upsertConversation({
        id: detail.id,
        title: detail.title,
        status: detail.status,
        updatedAt: detail.updatedAt,
        lastReportId: detail.lastReportId,
      })
    },
    appendMessages(messages: ConversationMessage[]) {
      this.currentConversation.messages.push(...messages)
      storage.set(CURRENT_CONVERSATION_KEY, this.currentConversation)
    },
    removeMessageById(id: string) {
      const index = this.currentConversation.messages.findIndex(m => m.id === id)
      if (index >= 0) {
        this.currentConversation.messages.splice(index, 1)
        storage.set(CURRENT_CONVERSATION_KEY, this.currentConversation)
      }
    },
    updateConversationStatus(status: ConversationDetail['status']) {
      this.currentConversation.status = status
      this.currentConversation.updatedAt = new Date().toISOString()
      if (this.currentConversation.id) {
        this.upsertConversation({
          id: this.currentConversation.id,
          title: this.currentConversation.title,
          status: this.currentConversation.status,
          updatedAt: this.currentConversation.updatedAt,
          lastReportId: this.currentConversation.lastReportId,
        })
      }
      storage.set(CURRENT_CONVERSATION_KEY, this.currentConversation)
    },
    setDrawerOpen(open: boolean) {
      this.isDrawerOpen = open
      storage.set(DRAWER_KEY, open)
    },
    setLoading(value: boolean) {
      this.isLoading = value
    },
    removeConversation(id: string) {
      this.conversations = this.conversations.filter(item => item.id !== id)
      storage.set(CONVERSATION_LIST_KEY, this.conversations)
    },
    resetCurrentConversation() {
      this.currentConversation = { ...emptyConversation }
      storage.remove(CURRENT_CONVERSATION_KEY)
    }
  }
})
