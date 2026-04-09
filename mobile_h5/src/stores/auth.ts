import { defineStore } from 'pinia'
import type { MobileUser } from '@/types/auth'
import { storage } from '@utils/storage'

const TOKEN_KEY = 'frontend_mobile_access_token'
const USER_KEY = 'frontend_mobile_user'
const EXTRA_KEYS = [
  'frontend_mobile_current_task',
  'frontend_mobile_task_draft',
  'frontend_mobile_current_conversation',
  'frontend_mobile_conversation_list',
  'frontend_mobile_drawer_open'
]

export const useAuthStore = defineStore('mobile-auth', {
  state: () => ({
    token: storage.get<string | null>(TOKEN_KEY, null),
    user: storage.get<MobileUser | null>(USER_KEY, null)
  }),
  getters: {
    isAuthenticated: state => Boolean(state.token)
  },
  actions: {
    setAuth(token: string, user: MobileUser) {
      this.token = token
      this.user = user
      storage.set(TOKEN_KEY, token)
      storage.set(USER_KEY, user)
    },
    clearAuth() {
      this.token = null
      this.user = null
      storage.remove(TOKEN_KEY)
      storage.remove(USER_KEY)
      EXTRA_KEYS.forEach(key => storage.remove(key))
    }
  }
})
