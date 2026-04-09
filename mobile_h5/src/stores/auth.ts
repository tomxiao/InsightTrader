import { defineStore } from 'pinia'
import type { MobileUser } from '@/types/auth'
import { storage } from '@utils/storage'

const TOKEN_KEY = 'frontend_mobile_access_token'
const USER_KEY = 'frontend_mobile_user'

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
    }
  }
})
