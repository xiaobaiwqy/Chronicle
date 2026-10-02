<script setup lang="ts">
import type { ChronicleEvent, Person } from '~/types/chronicle'
import { dynastyColor, dynastyOptions, yrRange } from '~/utils/dynasty'

const props = defineProps<{ persons: Person[]; events: ChronicleEvent[] }>()
const emit = defineEmits<{
  (e: 'select-person', id: number): void
  (e: 'select-event', id: number): void
  (e: 'select-dynasty', color: string): void
  (e: 'select-relation', id: number): void
}>()

const { graph } = useRelations()
const { dynasties } = useDynasties()

const query = ref('')
const open = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

type ResultType = 'person' | 'event' | 'dynasty' | 'relation'

interface Result {
  key: string
  type: ResultType
  id: number
  label: string
  sub: string
  color: string
  tag: string // 类型标注:人物 / 记录 / 朝代 / 关系
}

// 关系两端人物名映射(id -> 名字)
const personsById = computed(() => {
  const m = new Map<number, Person>()
  for (const p of props.persons) m.set(p.id, p)
  return m
})
const edges = computed(() => graph.value?.edges ?? [])

const results = computed<Result[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  const out: Result[] = []

  // 人物:姓名、简介、朝代
  for (const p of props.persons) {
    const hay = [p.name, p.summary, p.dynasty].join(' ').toLowerCase()
    if (hay.includes(q)) {
      out.push({
        key: `p${p.id}`,
        type: 'person',
        id: p.id,
        label: p.name,
        sub: p.birth_year != null ? yrRange(p.birth_year, p.death_year) : p.dynasty,
        color: p.color || dynastyColor(p.dynasty),
        tag: '人物',
      })
    }
  }

  // 记录:标题、描述、地点、朝代、参与人物
  for (const e of props.events) {
    const names = e.participants.map((x) => x.name).join(' ')
    const hay = [e.title, e.description, e.location || '', e.dynasty, names].join(' ').toLowerCase()
    if (hay.includes(q)) {
      out.push({
        key: `e${e.id}`,
        type: 'event',
        id: e.id,
        label: e.title,
        sub: `${yrRange(e.year_start, e.year_end)} · ${e.dynasty}`,
        color: dynastyColor(e.dynasty),
        tag: '记录',
      })
    }
  }

  // 朝代/国家:内置目录 + 自定义朝代 + 数据中出现过的自定义朝代
  for (const d of dynastyOptions(props.persons, dynasties.value)) {
    if (d.name.toLowerCase().includes(q)) {
      out.push({
        key: `d${d.name}`,
        type: 'dynasty',
        id: 0,
        label: d.name,
        sub: '朝代/国家',
        color: d.color,
        tag: '朝代',
      })
    }
  }

  // 关系:关系名 + 两端人物名
  for (const r of edges.value) {
    const from = personsById.value.get(r.from)
    const to = personsById.value.get(r.to)
    const hay = [r.label, from?.name || '', to?.name || ''].join(' ').toLowerCase()
    if (hay.includes(q)) {
      out.push({
        key: `r${r.id}`,
        type: 'relation',
        id: r.id,
        label: `${from?.name || '?'} ${r.directed ? '→' : '—'} ${to?.name || '?'}`,
        sub: `关系：${r.label}`,
        color: '#8e8e93',
        tag: '关系',
      })
    }
  }

  return out.slice(0, 10)
})

function onInput() {
  open.value = true
}

function onEnter() {
  const first = results.value[0]
  if (first) pick(first)
}

function pick(r: Result) {
  if (r.type === 'person') emit('select-person', r.id)
  else if (r.type === 'event') emit('select-event', r.id)
  else if (r.type === 'dynasty') emit('select-dynasty', r.color)
  else if (r.type === 'relation') emit('select-relation', r.id)
  query.value = ''
  open.value = false
  inputEl.value?.blur()
}

function onBlur() {
  // 延迟关闭,让点击结果先触发
  setTimeout(() => (open.value = false), 120)
}

function focus() {
  inputEl.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="searchbar" @click="focus">
    <span class="search-ic">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="6.5" />
        <path d="M20 20l-4.4-4.4" />
      </svg>
    </span>
    <input
      id="searchInput"
      ref="inputEl"
      v-model="query"
      placeholder="搜索人物、记录、朝代、关系…"
      @input="onInput"
      @keydown.enter="onEnter"
      @focus="open = !!query"
      @blur="onBlur"
    />
  </div>
  <div v-if="open && query.trim()" class="search-pop">
    <template v-if="results.length">
      <div v-for="r in results" :key="r.key" class="search-item" @mousedown.prevent="pick(r)">
        <span class="dot" :style="{ background: r.color }"></span>
        <div class="txt">
          <div class="t">{{ r.label }}</div>
          <div class="sub">{{ r.sub }}</div>
        </div>
        <span class="tag" :class="`tag-${r.type}`">{{ r.tag }}</span>
      </div>
    </template>
    <div v-else class="search-empty">无匹配结果</div>
  </div>
</template>
