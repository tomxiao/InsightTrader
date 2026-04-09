import { storeToRefs } from 'pinia'
import { useAuthStore } from '@stores/auth'

export const useAuth = () => {
  const authStore = useAuthStore()
  const { user, isAuthenticated } = storeToRefs(authStore)

  return {
    user,
    isAuthenticated,
    setAuth: authStore.setAuth,
    clearAuth: authStore.clearAuth
  }
}
