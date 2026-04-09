import { defineStore } from 'pinia'

export const useConversationStore = defineStore('mobile-conversation', {
  state: () => ({
    currentConversationId: '',
    currentTitle: '新会话'
  }),
  actions: {
    setConversation(id: string, title = '新会话') {
      this.currentConversationId = id
      this.currentTitle = title
    }
  }
})
