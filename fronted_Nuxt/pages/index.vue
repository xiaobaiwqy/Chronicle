<script setup lang="ts">
import type { PersonDetail } from '~/types/chronicle'

const view = ref<'graph' | 'timeline'>('graph')
const selectedPersonId = ref<number | null>(null)
const personDetail = ref<PersonDetail | null>(null)
const selectedEventId = ref<number | null>(null)
const dimmedRelationIds = ref<number[]>([])
const addOpen = ref(false)
const dynastyFilter = ref<string | null>(null)
const graphRef = ref<{
  focusPerson: (id: number) => void
  toggleEdgeHighlight: (id: number) => void
  highlightPersons: (ids: number[]) => void
} | null>(null)
const timelineRef = ref<{ focusEvent: (id: number) => void } | null>(null)

const { persons, fetchAll: fetchPersons, fetchDetail } = usePersons()
const { events, fetchAll: fetchEvents } = useEvents()
const { graph, fetchGraph } = useRelations()
const { fetchAll: fetchDynasties, ensure: ensureDynasties } = useDynasties()
const { fetchAll: fetchAvatars } = useAvatars()
const { message: toastMessage, visible: toastVisible, show: showToast } = useToast()

onMounted(async () => {
  try {
    // 先加载自定义朝代,确保颜色映射就绪后再构建关系网(节点颜色依赖它)
    await fetchDynasties()
    await Promise.all([fetchPersons(), fetchEvents(), fetchGraph(), fetchAvatars()])
    // 把已有人物里的自定义朝代(主+次)补录进自定义朝代表,确保它们出现在左上角筛选选框
    const names: string[] = []
    for (const p of persons.value) {
      if (p.dynasty) names.push(p.dynasty)
      if (p.secondary_dynasties?.length) names.push(...p.secondary_dynasties)
    }
    await ensureDynasties(names)
  } catch (err) {
    console.error('[Chronicle] 后端连接失败', err)
    showToast('无法连接后端服务 (http://127.0.0.1:8000)')
  }
})

const graphNodes = computed(() => graph.value?.nodes ?? [])
const graphEdges = computed(() => graph.value?.edges ?? [])
const graphReady = computed(() => graphNodes.value.length > 0)
const highlightId = computed(() => selectedPersonId.value)
const selectedEvent = computed(() => events.value.find((e) => e.id === selectedEventId.value) ?? null)

async function openPerson(id: number) {
  selectedPersonId.value = id
  // 搜索与点击头像效果一致:聚焦并放大该人物,镜头绕其旋转
  graphRef.value?.focusPerson(id)
  const detail = await fetchDetail(id)
  // 防止快速连续点击导致的乱序响应
  if (selectedPersonId.value === id) personDetail.value = detail
}

function closePerson() {
  selectedPersonId.value = null
  personDetail.value = null
}

// 点击人物(关系网/搜索/抽屉):先退出事件卡片,再打开人物
function onSelectPerson(id: number) {
  closeEvent()
  openPerson(id)
}

// 点击关系网空白处:关闭人物抽屉与事件卡片
function onBlank() {
  closePerson()
  closeEvent()
}

// 时间线/其它:点击事件聚焦首要参与人物,让对应的人在关系网中可见
function openEvent(id: number) {
  selectedEventId.value = id
  const ev = events.value.find((e) => e.id === id)
  const first = ev?.participants?.[0]
  if (first) graphRef.value?.focusPerson(first.person_id)
}

// 详情抽屉点击记录:保持聚焦当前人物,镜头不跳走(仅打开事件弹层)
function openEventFromDrawer(id: number) {
  selectedEventId.value = id
}

// 搜索框点击事件:不聚焦人,只点亮放大该事件的相关人物;时间线模式下同时定位放大到该事件
function openEventFromSearch(id: number) {
  selectedEventId.value = id
  const ev = events.value.find((e) => e.id === id)
  const ids = ev?.participants.map((x) => x.person_id) ?? []
  graphRef.value?.highlightPersons(ids)
  timelineRef.value?.focusEvent(id)
}

function closeEvent() {
  selectedEventId.value = null
  graphRef.value?.highlightPersons([]) // 关闭事件弹层:清除事件人物点亮
}

// 详情抽屉里点击某条关系:高亮该关系(多选),不跳转
function highlightRelation(id: number) {
  graphRef.value?.toggleEdgeHighlight(id)
}

// 关系网里被熄灭的连线(点一下翻转亮/暗):同步给详情抽屉的"关系"栏
function onEdgeDimChange(ids: number[]) {
  dimmedRelationIds.value = ids
}

// 搜索栏/左上角选框点击朝代/国家:统一筛选关系网与时间线
function filterDynasty(color: string) {
  dynastyFilter.value = color
}

// 切换朝代/国家筛选时,人物详情抽屉右滑退出(覆盖 DynastySelect v-model 与 SearchBar 两个入口)
watch(dynastyFilter, () => closePerson())

async function onRecorded() {
  await fetchEvents()
  const id = selectedPersonId.value
  if (id != null) await openPerson(id)
}

async function onAdded() {
  try {
    await Promise.all([fetchPersons(), fetchGraph(), fetchEvents()])
  } catch (err) {
    console.error('[Chronicle] 刷新数据失败', err)
  }
}

async function onUpdated() {
  try {
    await Promise.all([fetchPersons(), fetchGraph(), fetchEvents()])
    const id = selectedPersonId.value
    if (id != null) {
      const detail = await fetchDetail(id)
      personDetail.value = detail
    }
  } catch (err) {
    console.error('[Chronicle] 刷新数据失败', err)
  }
}

async function onDeleted() {
  closePerson()
  try {
    await Promise.all([fetchPersons(), fetchGraph(), fetchEvents()])
  } catch (err) {
    console.error('[Chronicle] 删除后刷新失败', err)
  }
}

function setView(v: 'graph' | 'timeline') {
  view.value = v
  closeEvent()
  closePerson()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    closePerson()
    closeEvent()
    addOpen.value = false
  }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    document.getElementById('searchInput')?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div id="stage">
    <div id="view-graph" :class="{ on: view === 'graph' }">
      <GraphView
        v-if="graphReady"
        ref="graphRef"
        :nodes="graphNodes"
        :edges="graphEdges"
        :highlight-id="highlightId"
        :active="view === 'graph'"
        :dynasty-filter="dynastyFilter"
        @select-person="onSelectPerson"
        @select-blank="onBlank"
        @edge-dim-change="onEdgeDimChange"
        @clear-dynasty-filter="dynastyFilter = null"
      />
    </div>
    <div id="view-timeline" :class="{ on: view === 'timeline' }">
      <TimelineView
        ref="timelineRef"
        :events="events"
        :selected-event-id="selectedEventId"
        :active="view === 'timeline'"
        :dynasty-filter="dynastyFilter"
        @select-event="openEvent"
      />
    </div>
  </div>

  <DynastySelect v-model="dynastyFilter" :persons="persons" />
  <SideRail :model-value="view" @update:model-value="setView" />
  <SearchBar
    :persons="persons"
    :events="events"
    @select-person="onSelectPerson"
    @select-event="openEventFromSearch"
    @select-dynasty="filterDynasty"
    @select-relation="highlightRelation"
  />
  <button class="add-btn" title="添加人物 / 关系 / 记录" @click="addOpen = true">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  </button>
  <PersonDrawer
    :open="!!personDetail"
    :detail="personDetail"
    :dimmed-relations="dimmedRelationIds"
    :dismiss-on-outside="view === 'timeline'"
    @close="closePerson"
    @select-person="onSelectPerson"
    @select-event="openEventFromDrawer"
    @highlight-relation="highlightRelation"
    @recorded="onRecorded"
    @updated="onUpdated"
    @deleted="onDeleted"
  />
  <AddPanel :open="addOpen" :persons="persons" @close="addOpen = false" @saved="onAdded" />
  <EventPopover :event="selectedEvent" @close="closeEvent" @select-person="openPerson" />
  <div class="toast" :class="{ show: toastVisible }"><span>{{ toastMessage }}</span></div>
</template>
