export interface ManagedUser {
  id: string
  username: string
  displayName?: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  lastLoginAt?: string | null
  createdAt: string
  updatedAt: string
}

export interface CreateManagedUserRequest {
  username: string
  displayName?: string
  password: string
}

export interface UpdateManagedUserStatusRequest {
  status: 'active' | 'disabled'
}

export interface ResetManagedUserPasswordRequest {
  password: string
}
