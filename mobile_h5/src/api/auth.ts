import type { LoginRequest, LoginResponse, LogoutResponse } from '@/types/auth'
import { request } from './request'

export const authApi = {
  login(payload: LoginRequest) {
    return request.post<LoginResponse>('/auth/login', payload).then(response => response.data)
  },
  logout() {
    return request.post<LogoutResponse>('/auth/logout').then(response => response.data)
  }
}
