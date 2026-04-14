import axios from 'axios'
import { env } from '@utils/env'
import { useAuthStore } from '@stores/auth'

export const request = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 15000
})

request.interceptors.request.use(config => {
  const authStore = useAuthStore()

  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }

  return config
})

request.interceptors.response.use(
  response => response,
  error => {
    const isAxios = axios.isAxiosError(error)
    const isLoginRequest = isAxios && error.config?.url?.endsWith('/auth/login')

    if (error.response?.status === 401 && !isLoginRequest) {
      const authStore = useAuthStore()
      authStore.clearAuth()

      if (typeof window !== 'undefined') {
        window.location.replace('/login')
      }
    }

    if (isAxios && typeof error.response?.data?.detail === 'string') {
      error.message = error.response.data.detail
    }

    return Promise.reject(error)
  }
)
