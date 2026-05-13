/// <reference types="vite/client" />

import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  /** DevBox 经 Sealos HTTPS 公网访问时，在 frontend/.env.development.local 中设置（无 https://） */
  const sealosDevHost = env.SEALOS_DEV_PUBLIC_HOST?.trim()

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      // Sealos DevBox 对外映射常用 8080；控制台「预览」请指向本端口
      port: 8080,
      strictPort: true,
      // 经 HTTPS 域名访问时，让 HMR WebSocket 走 wss:443（不设则热更新可能失败）
      ...(sealosDevHost
        ? {
            hmr: {
              protocol: 'wss',
              host: sealosDevHost,
              clientPort: 443,
            },
          }
        : {}),
      // 花生壳 / DevBox / Sealos 公网：放行 Host，避免 “Blocked request … host is not allowed”
      allowedHosts: ['.vicp.fun', '1023700ehma00.vicp.fun', 'devbox.ns-1ht608x0', '.sealosbja.site', 'fhlkzwzoizzu.sealosbja.site'],
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 8080,
      strictPort: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
