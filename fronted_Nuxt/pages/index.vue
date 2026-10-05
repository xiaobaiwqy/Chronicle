<script setup lang="ts">
import type { PersonDetail } from '~/types/chronicle'
import { defaultUnlitDynastyNames, toggleableDynastyBands } from '~/utils/dynasty'

const view = ref<'graph' | 'timeline'>('graph')
const selectedPersonId = ref<number | null>(null)
const personDetail = ref<PersonDetail | null>(null)
const selectedEventId = ref<number | null>(null)
const dimmedRelationIds = ref<number[]>([])
const addOpen = ref(false)
const libraryOpen = ref(false)
const dynastyFilter = ref<string[]>([])
// 点亮/熄灭是两套独立状态,分别驱动两个视图(与 dynastyFilter「打勾筛选事件/人物」也是独立的一套):
// - graphUnlit(关系网):按朝代标签"名字"显隐人物,与时间无关;默认空 → 全部点亮 → 全部人物显示。
// - timelineUnlit(时间线):按时间分块显隐,因时间重叠不能默认全显,默认熄灭与宏观分块重叠的细分/自定义朝代。
const graphUnlit = ref<string[]>([])
const timelineUnlit = ref<string[]>([])
const timelineMode = ref<'events' | 'people'>('events')
const graphRef = ref<{
  focusPerson: (id: number) => void
  toggleEdgeHighlight: (id: number) => void
  highlightPersons: (ids: number[]) => void
  resetToGlobal: () => void
} | null>(null)
const timelineRef = ref<{ focusEvent: (id: number) => void } | null>(null)

const { persons, fetchAll: fetchPersons, fetchDetail } = usePersons()
const { events, fetchAll: fetchEvents } = useEvents()
const { graph, fetchGraph } = useRelations()
const { dynasties, fetchAll: fetchDynasties, ensure: ensureDynasties } = useDynasties()
// 已见过的"默认应熄灭"朝代:新增自定义朝代时只补入首次出现者,不覆盖用户已手动点亮/熄灭的选择。
const seenDefaultUnlit = new Set<string>()

// 时间线关系链同步:自定义朝代(含起止年)→ 可点亮分块 → 与宏观分块时间重叠者默认熄灭 → timelineUnlit。
// 随自定义朝代增删自动同步:新增的"默认应熄灭"项补入、已删除的朝代清除残留名,用户手动选择不受影响。
function syncDefaultUnlit() {
  const bands = toggleableDynastyBands(dynasties.value)
  const alive = new Set(bands.map((b) => b.name))
  // 清除已不存在的朝代残留(被删除、或去掉了起止年)
  timelineUnlit.value = timelineUnlit.value.filter((n) => alive.has(n))
  for (const n of [...seenDefaultUnlit]) if (!alive.has(n)) seenDefaultUnlit.delete(n)
  // 补入首次出现的"默认应熄灭"项(内置细分朝代 + 与宏观分块时间重叠的自定义朝代)
  const defaults = defaultUnlitDynastyNames(dynasties.value)
  const fresh = defaults.filter((n) => !seenDefaultUnlit.has(n) && !timelineUnlit.value.includes(n))
  if (fresh.length) timelineUnlit.value = [...timelineUnlit.value, ...fresh]
  defaults.forEach((n) => seenDefaultUnlit.add(n))
}
watch(dynasties, syncDefaultUnlit, { immediate: true })

// 左上角选框展示/操作的"点亮/熄灭"清单随当前视图切换:关系网操作 graphUnlit,时间线操作 timelineUnlit。
const activeUnlit = computed(() => (view.value === 'graph' ? graphUnlit.value : timelineUnlit.value))
function onUnlitChange(names: string[]) {
  if (view.value === 'graph') graphUnlit.value = names
  else timelineUnlit.value = names
}
const { fetchAll: fetchAvatars } = useAvatars()
const { message: toastMessage, visible: toastVisible, show: showToast } = useToast()

onMounted(async () => {
  try {
    // 先加载自定义朝代,确保颜色映射就绪后再构建关系网(节点颜色依赖它)
    await fetchDynasties()
    // 默认熄灭已由 watch(dynasties) 同步:细分朝代 + 与宏观分块时间重叠的自定义朝代(避免默认状态即出现重叠分块)
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

async function openPerson(id: number, focusGraph = true) {
  selectedPersonId.value = id
  // 搜索与点击头像效果一致:聚焦并放大该人物,镜头绕其旋转(时间线来源不聚焦,避免影响关系网排布)
  if (focusGraph) graphRef.value?.focusPerson(id)
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

// 时间线点击头像:只打开人物抽屉,不聚焦/重排关系网(两个视图的状态隔开)
function onTimelinePerson(id: number) {
  closeEvent()
  openPerson(id, false)
}

// 点击关系网空白处:仅单人物/事件聚焦回退(关抽屉/事件);群体(朝代筛选)保留,不轻易退出。
function onBlank() {
  if (selectedPersonId.value != null) closePerson()
  if (selectedEventId.value != null) closeEvent()
}

// 一键回到初始界面:退出聚焦/筛选/事件组/熄灭连线,并重置关系网"点亮/熄灭"(左上角选框状态同步归零)
function resetGlobal() {
  closePerson()
  closeEvent()
  dynastyFilter.value = []
  graphUnlit.value = []
  dimmedRelationIds.value = []
  graphRef.value?.resetToGlobal()
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

// 搜索栏/左上角选框点击朝代/国家:统一筛选关系网与时间线(多选:点一下选中,再点取消)
function filterDynasty(color: string) {
  const i = dynastyFilter.value.indexOf(color)
  if (i >= 0) dynastyFilter.value = dynastyFilter.value.filter((c) => c !== color)
  else dynastyFilter.value = [...dynastyFilter.value, color]
}

// 人物高亮与朝代筛选互斥(仅显示层):关系网里人物聚焦优先、朝代作为背景被压暗;
// 但朝代筛选本身保留(不清空),点空白回退时恢复朝代高亮。
// 反向:切朝代/国家筛选时关闭人物抽屉(覆盖 DynastySelect v-model 与 SearchBar)。
// 仅在筛选非空时关闭:清空筛选(点空白回退到自由视角)不应反过来关闭刚打开的人物。
watch(dynastyFilter, (filter) => {
  if (filter.length && selectedPersonId.value != null) closePerson()
})

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

// 库界面增删改后:统一刷新人物/关系网/事件;若当前详情人物被删则关闭抽屉
async function onLibraryChanged() {
  try {
    await Promise.all([fetchPersons(), fetchGraph(), fetchEvents()])
    if (selectedPersonId.value != null && !persons.value.some((p) => p.id === selectedPersonId.value)) {
      closePerson()
    }
  } catch (err) {
    console.error('[Chronicle] 库刷新失败', err)
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
    libraryOpen.value = false
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
        :unlit-dynasties="graphUnlit"
        @select-person="onSelectPerson"
        @select-blank="onBlank"
        @edge-dim-change="onEdgeDimChange"
      />
    </div>
    <div id="view-timeline" :class="{ on: view === 'timeline' }">
      <TimelineView
        ref="timelineRef"
        :events="events"
        :persons="persons"
        :mode="timelineMode"
        :selected-event-id="selectedEventId"
        :selected-person-id="selectedPersonId"
        :active="view === 'timeline'"
        :dynasty-filter="dynastyFilter"
        :unlit-dynasties="timelineUnlit"
        @select-event="openEvent"
        @select-person="onTimelinePerson"
      />
    </div>
  </div>

  <div class="topbar">
    <button class="lib-btn" title="人物库 / 事件库" @click="libraryOpen = true">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 5a2 2 0 0 1 2-2h5v18H6a2 2 0 0 1-2-2z" />
        <path d="M18 3h-5v18h5a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z" />
      </svg>
    </button>
    <DynastySelect v-model="dynastyFilter" :unlit="activeUnlit" :mode="view" :persons="persons" @update:unlit="onUnlitChange" />
    <SideRail :model-value="view" @update:model-value="setView" />
    <Transition name="tl-switch">
      <div v-if="view === 'timeline'" class="tl-mode-switch">
        <button :class="{ on: timelineMode === 'events' }" @click="timelineMode = 'events'">事件</button>
        <button :class="{ on: timelineMode === 'people' }" @click="timelineMode = 'people'">人物</button>
      </div>
    </Transition>
  </div>
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
  <button v-if="view === 'graph'" class="global-btn" title="回到初始界面" @click="resetGlobal">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18Z" />
    </svg>
    <span class="tip">回到初始界面</span>
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
  <LibraryView :open="libraryOpen" @close="libraryOpen = false" @changed="onLibraryChanged" />
  <EventPopover :event="selectedEvent" @close="closeEvent" @select-person="openPerson" />
  <div class="toast" :class="{ show: toastVisible }"><span>{{ toastMessage }}</span></div>
</template>
