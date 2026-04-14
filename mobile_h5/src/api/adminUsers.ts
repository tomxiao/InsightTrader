import type {
  CreateManagedUserRequest,
  ManagedUser,
  ResetManagedUserPasswordRequest,
  UpdateManagedUserStatusRequest,
} from '@/types/adminUsers'
import { request } from './request'

export const adminUsersApi = {
  listUsers() {
    return request.get<ManagedUser[]>('/admin/users').then(response => response.data)
  },
  createUser(payload: CreateManagedUserRequest) {
    return request.post<ManagedUser>('/admin/users', payload).then(response => response.data)
  },
  updateUserStatus(userId: string, payload: UpdateManagedUserStatusRequest) {
    return request.patch<ManagedUser>(`/admin/users/${userId}/status`, payload).then(response => response.data)
  },
  resetPassword(userId: string, payload: ResetManagedUserPasswordRequest) {
    return request.post<ManagedUser>(`/admin/users/${userId}/reset-password`, payload).then(response => response.data)
  }
}
