import api from './api'

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface User {
  username: string
  sub: string
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/api/auth/login', {
      username,
      password,
    })
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/api/auth/me')
    return response.data
  },

  logout() {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token')
  }
}


