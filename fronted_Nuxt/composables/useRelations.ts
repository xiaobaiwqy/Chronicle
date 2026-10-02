import type { GraphData, Relation } from '~/types/chronicle'

export interface RelationCreatePayload {
  from_person_id: number
  to_person_id: number
  label: string
  directed: boolean
}

export function useRelations() {
  const api = useBackendApi()
  const graph = useState<GraphData | null>('chronicle-graph', () => null)

  async function fetchGraph(): Promise<GraphData> {
    graph.value = await api<GraphData>('/graph')
    return graph.value
  }

  function fetchAll(): Promise<Relation[]> {
    return api<Relation[]>('/relations')
  }

  async function createRelation(payload: RelationCreatePayload): Promise<Relation> {
    return api<Relation>('/relations', { method: 'POST', body: payload })
  }

  async function removeRelation(id: number): Promise<void> {
    await api<void>(`/relations/${id}`, { method: 'DELETE' })
  }

  return { graph, fetchGraph, fetchAll, createRelation, removeRelation }
}
