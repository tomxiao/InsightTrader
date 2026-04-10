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
    user: storage.get<MobileUser | null>(USER_KEY, null),
    hasCheckedSession: false
  }),
  getters: {
    isAuthenticated: state => Boolean(state.token && state.user)
  },
  actions: {
    setAuth(token: string, user: MobileUser) {
      this.token = token
      this.user = user
      this.hasCheckedSession = true
      storage.set(TOKEN_KEY, token)
      storage.set(USER_KEY, user)
    },
    setUser(user: MobileUser | null) {
      this.user = user
      if (user) {
        storage.set(USER_KEY, user)
      } else {
        storage.remove(USER_KEY)
      }
    },
    markSessionChecked(value = true) {
      this.hasCheckedSession = value
    },
    clearAuth() {
      this.token = null
      this.user = null
      this.hasCheckedSession = true
      storage.remove(TOKEN_KEY)
      storage.remove(USER_KEY)
      EXTRA_KEYS.forEach(key => storage.remove(key))
    }
  }
})
