/**
 * 统一的后端请求封装(参考 DMS)。
 * 开发环境默认走 Nuxt devProxy('/api' -> http://127.0.0.1:8000)。
 */
export function useBackendApi() {
  const config = useRuntimeConfig()
  const base = (config.public.apiBase as string) || '/api'
  return $fetch.create({
    baseURL: `${base}/v1`,
    headers: { Accept: 'application/json' },
  })
}
