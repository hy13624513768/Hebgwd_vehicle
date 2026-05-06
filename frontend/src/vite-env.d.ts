/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 可选。生产构建若前后端不同域，填后端根地址，如 https://api.example.com（不要尾斜杠） */
  readonly VITE_API_BASE_URL?: string
  /** 可选。development / staging / production，仅用于前端区分展示或打包标识 */
  readonly VITE_APP_ENV?: string
  readonly VITE_AMAP_KEY?: string
  readonly VITE_AMAP_SECURITY_JSCODE?: string
}
