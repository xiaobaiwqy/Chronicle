import type { ChronicleEvent } from '~/types/chronicle'

export interface EventCreatePayload {
  title: string
  description: string
  year_start: number
  year_end: number
  dynasty: string
  participants: { person_id: number; role: string }[]
}

export function useEvents() {
  const api = useBackendApi()
  const events = useState<ChronicleEvent[]>('chronicle-events', () => [])

  async function fetchAll(): Promise<ChronicleEvent[]> {
    events.value = await api<ChronicleEvent[]>('/events')
    return events.value
  }

  async function create(payload: EventCreatePayload): Promise<ChronicleEvent> {
    return api<ChronicleEvent>('/events', { method: 'POST', body: payload })
  }

  async function remove(id: number): Promise<void> {
    await api<void>(`/events/${id}`, { method: 'DELETE' })
  }

  return { events, fetchAll, create, remove }
}
