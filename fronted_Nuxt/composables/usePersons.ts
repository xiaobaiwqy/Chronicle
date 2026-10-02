import type { Person, PersonDetail } from '~/types/chronicle'

export interface PersonCreatePayload {
  name: string
  dynasty?: string
  secondary_dynasties?: string[]
  birth_year?: number | null
  death_year?: number | null
  summary?: string
  identity?: string
  color?: string
  avatar?: string
}

export interface PersonUpdatePayload {
  name?: string
  dynasty?: string
  secondary_dynasties?: string[]
  birth_year?: number | null
  death_year?: number | null
  summary?: string
  identity?: string
  color?: string
  avatar?: string
}

export function usePersons() {
  const api = useBackendApi()
  const persons = useState<Person[]>('chronicle-persons', () => [])
  const loading = useState<boolean>('chronicle-persons-loading', () => false)

  async function fetchAll(): Promise<Person[]> {
    loading.value = true
    try {
      persons.value = await api<Person[]>('/persons')
      return persons.value
    } finally {
      loading.value = false
    }
  }

  function fetchDetail(id: number): Promise<PersonDetail> {
    return api<PersonDetail>(`/persons/${id}/detail`)
  }

  async function create(payload: PersonCreatePayload): Promise<Person> {
    return api<Person>('/persons', { method: 'POST', body: payload })
  }

  async function update(id: number, payload: PersonUpdatePayload): Promise<Person> {
    return api<Person>(`/persons/${id}`, { method: 'PUT', body: payload })
  }

  async function remove(id: number): Promise<void> {
    await api<void>(`/persons/${id}`, { method: 'DELETE' })
  }

  const byId = computed<Map<number, Person>>(() => {
    const m = new Map<number, Person>()
    for (const p of persons.value) m.set(p.id, p)
    return m
  })

  return { persons, loading, fetchAll, fetchDetail, create, update, remove, byId }
}
