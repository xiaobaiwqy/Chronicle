import type { CustomDynasty } from '~/types/chronicle'
import { DYNASTY_CATALOG, TIMELINE_BANDS, hashColor, setCustomDynastyColors } from '~/utils/dynasty'

export interface CustomDynastyCreatePayload {
  name: string
  color: string
  start_year?: number | null
  end_year?: number | null
}

export interface CustomDynastyUpdatePayload {
  name?: string
  color?: string
  start_year?: number | null
  end_year?: number | null
}

export function useDynasties() {
  const api = useBackendApi()
  const dynasties = useState<CustomDynasty[]>('chronicle-custom-dynasties', () => [])

  async function fetchAll(): Promise<CustomDynasty[]> {
    dynasties.value = await api<CustomDynasty[]>('/custom-dynasties')
    setCustomDynastyColors(dynasties.value)
    return dynasties.value
  }

  async function create(payload: CustomDynastyCreatePayload): Promise<CustomDynasty> {
    const created = await api<CustomDynasty>('/custom-dynasties', { method: 'POST', body: payload })
    await fetchAll()
    return created
  }

  async function update(id: number, payload: CustomDynastyUpdatePayload): Promise<CustomDynasty> {
    const updated = await api<CustomDynasty>(`/custom-dynasties/${id}`, { method: 'PUT', body: payload })
    await fetchAll()
    return updated
  }

  async function remove(id: number): Promise<void> {
    await api<void>(`/custom-dynasties/${id}`, { method: 'DELETE' })
    await fetchAll()
  }

  // 确保一组朝代/国家名已注册为自定义朝代:不在内置名单、也不在现有自定义表里的会自动补录。
  // 用于新增/编辑人物时,把输入的自定义朝代同步进左上角筛选选框。
  // 内置 = 目录细分(DYNASTY_CATALOG)+ 宏观时间色带(TIMELINE_BANDS),
  // 「汉/晋」等只作为色带存在、未入目录的朝代名,不应再被当成自定义朝代补录。
  const builtin = new Set([...DYNASTY_CATALOG.map((d) => d.name), ...TIMELINE_BANDS.map((b) => b.name)])
  async function ensure(names: string[]): Promise<void> {
    const existing = new Set(dynasties.value.map((d) => d.name))
    const pending = [...new Set(names.filter((n) => n && n.trim() && !builtin.has(n.trim()) && !existing.has(n.trim())))]
    if (!pending.length) return
    for (const raw of pending) {
      const name = raw.trim()
      try {
        await create({ name, color: hashColor(name) })
      } catch (err) {
        console.error('[Chronicle] 补录自定义朝代失败', name, err)
      }
    }
  }

  return { dynasties, fetchAll, create, update, remove, ensure }
}
