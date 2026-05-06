import { defineStore } from 'pinia'

import * as authApi from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: (localStorage.getItem('access_token') ?? '') as string,
    profile: null as null | authApi.UserInfo,
  }),
  actions: {
    async login(payload: { username: string; password: string; slider_session_id: string }) {
      const res = await authApi.login(payload)
      this.token = res.access_token
      this.profile = res.user
      localStorage.setItem('access_token', this.token)
    },
    async fetchMe() {
      this.profile = await authApi.me()
    },
    logout() {
      this.token = ''
      this.profile = null
      localStorage.removeItem('access_token')
    },
  },
})
