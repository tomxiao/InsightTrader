import { request } from './request'

export const userApi = {
  getCurrentUser() {
    return request.get('/auth/me')
  }
}
