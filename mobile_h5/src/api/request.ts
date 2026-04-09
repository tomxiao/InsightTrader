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
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.clearAuth()
    }

    return Promise.reject(error)
  }
)
