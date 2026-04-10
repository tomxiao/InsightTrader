export interface MobileUser {
  id: string
  username: string
  displayName?: string
  role: 'user' | 'admin'
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  expires_in: number
  refresh_token?: string
  user: MobileUser
}

export interface LogoutResponse {
  ok: boolean
}
