import { defineStore } from 'pinia'

export const useUserStore = defineStore('mobile-user', {
  state: () => ({
    hasHydrated: false
  }),
  actions: {
    markHydrated() {
      this.hasHydrated = true
    }
  }
})
