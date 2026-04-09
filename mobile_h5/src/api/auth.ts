import type { LoginRequest, LoginResponse } from '@/types/auth'
import { request } from './request'

export const authApi = {
  login(payload: LoginRequest) {
    return request.post<LoginResponse>('/auth/login', payload).then(response => response.data)
  }
}
