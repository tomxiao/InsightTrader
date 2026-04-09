export interface MobileUser {
  id: string
  username: string
  displayName?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token?: string
  user: MobileUser
}
