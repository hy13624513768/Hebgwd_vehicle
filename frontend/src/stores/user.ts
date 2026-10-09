import { defineStore } from 'pinia'

import * as authApi from '@/api/auth'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/authToken'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getAccessToken(),
    profile: null as null | authApi.UserInfo,
  }),
  actions: {
    async login(payload: { username: string; password: string }) {
      const res = await authApi.login(payload)
      this.token = res.access_token
      this.profile = res.user
      setAccessToken(this.token)
    },
    async fetchMe() {
      this.profile = await authApi.me()
    },
    logout() {
      this.token = ''
      this.profile = null
      clearAccessToken()
    },
  },
})
