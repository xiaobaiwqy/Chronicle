// 后端源地址:默认 8000,如该端口被占用可用环境变量覆盖,
// 例如 CHRONICLE_BACKEND_ORIGIN=http://127.0.0.1:8001 npm run dev
const backendOrigin = process.env.CHRONICLE_BACKEND_ORIGIN || 'http://127.0.0.1:8000'

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      // 前端请求后端 API 的基地址。开发环境走 devProxy('/api' -> backendOrigin)，
      // 如代理失效可设 NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api 直连。
      apiBase: '/api',
    },
  },

  // 开发环境代理:把 /api/** 转发到后端。
  // 注意:h3 的 app.use('/api') 会剥掉 /api 前缀,后端收到的是 /v1/...,
  // 故 target 需带上 /api 后缀,借 http-proxy 的 prependPath 拼回 /api/v1/...
  nitro: {
    devProxy: {
      '/api': {
        target: `${backendOrigin}/api`,
        changeOrigin: true,
      },
    },
  },

  app: {
    head: {
      title: '人物志',
      htmlAttrs: { lang: 'zh-CN' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1.0' },
      ],
    },
  },
})
