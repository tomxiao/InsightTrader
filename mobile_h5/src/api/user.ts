import { request } from './request'
import type { MobileUser } from '@/types/auth'

export const userApi = {
  getCurrentUser() {
    return request.get<MobileUser>('/auth/me').then(response => response.data)
  }
}
