import axios from 'axios'
import { clearAccessToken, getAccessToken } from '@/lib/authToken'

const apiRoot = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
export const http = axios.create({
  baseURL: apiRoot ? `${apiRoot}/api/v1` : '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  response => response,
  error => {
    const isLogin = String(error.config?.url ?? '').includes('/auth/login')
    if (error.response?.status === 401 && !isLogin) {
      clearAccessToken()
      if (window.location.pathname !== '/login') {
        window.location.replace('/login?redirect=' + encodeURIComponent(window.location.pathname + window.location.search))
      }
    }
    return Promise.reject(error)
  },
)
