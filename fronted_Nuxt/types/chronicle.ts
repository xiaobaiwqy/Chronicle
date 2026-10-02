// 前后端共用的数据形状(与后端 /api/v1 返回一一对应)

export interface Person {
  id: number
  name: string
  dynasty: string
  secondary_dynasties: string[]
  birth_year: number | null
  death_year: number | null
  summary: string
  identity: string
  color: string
  avatar: string
  avatar_url: string
}

export interface EventParticipant {
  person_id: number
  role: string
  name: string
  color: string
  dynasty: string
}

export interface ChronicleEvent {
  id: number
  title: string
  description: string
  year_start: number
  year_end: number
  dynasty: string
  location: string | null
  participants: EventParticipant[]
}

export interface CustomDynasty {
  id: number
  name: string
  color: string
}

export interface Relation {
  id: number
  from_person_id: number
  to_person_id: number
  label: string
  directed: boolean
}

export interface DetailRelation extends Relation {
  other_id: number
  other_name: string
  other_color: string
}

export interface GraphEdge {
  id: number
  from: number
  to: number
  label: string
  directed: boolean
}

export interface GraphData {
  nodes: Person[]
  edges: GraphEdge[]
}

export interface PersonDetail {
  person: Person
  events: ChronicleEvent[]
  relations: DetailRelation[]
}

// 内置下拉选框(AppSelect)的选项
export interface SelectOption {
  value: number | string
  label: string
  color?: string
}

// 默认头像库里的一个头像(名字 + 访问 URL)
export interface AvatarOption {
  name: string
  url: string
}
