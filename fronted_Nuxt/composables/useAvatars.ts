import type { AvatarOption } from '~/types/chronicle'

/**
 * 默认头像库:local_data/avatars 里按人物名命名的图片。
 * 用于「从库里选择头像」的弹层,以及按名自动匹配的默认头像。
 */
export function useAvatars() {
  const api = useBackendApi()
  const avatars = useState<AvatarOption[]>('chronicle-avatars', () => [])

  async function fetchAll(): Promise<AvatarOption[]> {
    avatars.value = await api<AvatarOption[]>('/avatars')
    return avatars.value
  }

  // 名字 -> URL 的映射(自动匹配用)
  const byName = computed<Map<string, string>>(() => {
    const m = new Map<string, string>()
    for (const a of avatars.value) m.set(a.name, a.url)
    return m
  })

  // 按人物名匹配默认头像;无匹配返回空串
  function urlFor(name: string): string {
    return byName.value.get(name) ?? ''
  }

  return { avatars, fetchAll, byName, urlFor }
}
