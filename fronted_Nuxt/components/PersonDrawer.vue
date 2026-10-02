<script setup lang="ts">
import type { ChronicleEvent, PersonDetail, SelectOption } from '~/types/chronicle'
import { dynastyColor, dynastyOptions, parseYear, yrRange } from '~/utils/dynasty'

const props = defineProps<{ open: boolean; detail: PersonDetail | null; dimmedRelations?: number[]; dismissOnOutside?: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select-person', id: number): void
  (e: 'select-event', id: number): void
  (e: 'highlight-relation', id: number): void
  (e: 'recorded'): void
  (e: 'updated'): void
  (e: 'deleted'): void
}>()

const { persons, update: updatePerson, remove: removePerson } = usePersons()
const { createRelation, removeRelation } = useRelations()
const { create, update: updateEvent, remove: removeEvent } = useEvents()
const { dynasties, ensure } = useDynasties()
const { urlFor } = useAvatars()
const toast = useToast()

// 实际渲染的内容与抽屉显隐:切换人物时整个卡片先退出再进入
const shown = ref(false)
const display = ref<PersonDetail | null>(null)

watch(
  () => props.open,
  (on) => {
    if (on) {
      display.value = props.detail
      shown.value = true
    } else {
      shown.value = false // 滑出;display 保留到滑出完成
    }
  },
)

// 切换人物:回到只读主页并清残留状态;已打开状态下切换时整个卡片先退出再滑入
watch(
  () => props.detail?.person.id,
  (id, prevId) => {
    if (id === prevId) return
    editing.value = false
    confirmDelete.value = false
    confirmDel.value = null
    showForm.value = false
    selEvents.value = new Set()
    if (props.open && prevId != null && id != null) {
      shown.value = false
      setTimeout(() => {
        if (!props.open) return
        display.value = props.detail
        shown.value = true
      }, 300)
    }
  },
)

// 同一人物数据刷新(编辑保存 / 增删关系记录后):直接同步显示,不做退出动画
watch(
  () => props.detail,
  (detail) => {
    if (!detail || !display.value) return
    if (detail.person.id === display.value.person.id) display.value = detail
  },
)

const data = computed<PersonDetail | null>(() => display.value)

const editing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const confirmDelete = ref(false)
// 二次确认:关系删除 / 批量删除记录,首击进入待确认,再击才真正删除;3 秒无操作自动复位
const confirmDel = ref<null | { kind: 'rel'; id: number } | { kind: 'batch' }>(null)
let confirmDelTimer: ReturnType<typeof setTimeout> | null = null
function armConfirm(v: NonNullable<typeof confirmDel.value>) {
  confirmDel.value = v
  if (confirmDelTimer) clearTimeout(confirmDelTimer)
  confirmDelTimer = setTimeout(() => (confirmDel.value = null), 3000)
}

// —— 基础信息编辑 ——
const form = reactive({
  name: '',
  dynasty: '',
  identities: [] as string[],
  birth: '',
  death: '',
  summary: '',
  color: '',
  avatar: '',
  secondaryDynasties: [] as string[],
})
const dynOptions = computed(() => dynastyOptions(persons.value, dynasties.value))
// 下拉选框选项(朝代 / 关系目标),与添加面板共用 AppSelect 的 {value,label,color} 结构
const dynastySelectOptions = computed<SelectOption[]>(() =>
  dynOptions.value.map((d) => ({ value: d.name, label: d.name, color: d.color })),
)
// 次朝代选项 = 完整目录,排除已选主朝代(避免主次重复同一项)
const secondaryDynastyOptions = computed<SelectOption[]>(() =>
  dynastySelectOptions.value.filter((o) => String(o.value) !== form.dynasty.trim()),
)
// 主朝代变化时,从次朝代里移除同名项,保持主次不重复
watch(
  () => form.dynasty,
  (d) => {
    const main = d.trim()
    if (main && form.secondaryDynasties.includes(main))
      form.secondaryDynasties = form.secondaryDynasties.filter((x) => x !== main)
  },
)
const personOptions = computed<SelectOption[]>(() => {
  const pid = data.value?.person.id
  return persons.value.filter((p) => p.id !== pid).map((p) => ({ value: p.id, label: p.name, color: p.color || dynastyColor(p.dynasty) }))
})
// 姓名重名实时校验(排除当前人物):输入完名字即提示并标红
const nameDup = computed(() => {
  const pid = data.value?.person.id
  const n = form.name.trim()
  return !!n && persons.value.some((p) => p.id !== pid && p.name.trim() === n)
})
// 颜色:默认跟随朝代,可手动覆盖(取色面板见 ColorPicker 组件)
const pColor = computed(() => form.color || dynastyColor(form.dynasty.trim()))

// 头像:上传图片,否则回退到姓名首字
const avatarInput = ref<HTMLInputElement | null>(null)
function pickAvatar() {
  avatarInput.value?.click()
}
function onAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    toast.show('请选择图片文件')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    toast.show('图片请小于 2MB')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    form.avatar = String(reader.result)
  }
  reader.readAsDataURL(file)
  input.value = '' // 允许重复选择同一文件
}

// 默认头像库:弹层里选择,或按名自动匹配
const avOpen = ref(false)
const avatarPreview = computed(() => form.avatar || urlFor(form.name.trim()))
function onPickLibrary(url: string) {
  form.avatar = url
  avOpen.value = false
}

function startEdit() {
  const p = data.value?.person
  if (!p) return
  form.name = p.name
  form.dynasty = p.dynasty
  form.identities = (p.identity || '').split('、').filter(Boolean)
  form.birth = p.birth_year != null ? String(p.birth_year) : ''
  form.death = p.death_year != null ? String(p.death_year) : ''
  form.summary = p.summary || ''
  form.color = p.color || ''
  form.avatar = p.avatar || ''
  form.secondaryDynasties = [...(p.secondary_dynasties || [])]
  selEvents.value = new Set()
  relForm.target = 0
  relForm.label = ''
  relForm.dir = 0
  showForm.value = false
  editing.value = true
}

// 重置基础信息表单为人物原始数据(撤销未保存的修改)
function resetBasic() {
  const p = data.value?.person
  if (!p) return
  form.name = p.name
  form.dynasty = p.dynasty
  form.identities = (p.identity || '').split('、').filter(Boolean)
  form.birth = p.birth_year != null ? String(p.birth_year) : ''
  form.death = p.death_year != null ? String(p.death_year) : ''
  form.summary = p.summary || ''
  form.color = p.color || ''
  form.avatar = p.avatar || ''
  form.secondaryDynasties = [...(p.secondary_dynasties || [])]
}

function toggleEdit() {
  if (editing.value) editing.value = false
  else startEdit()
}

async function saveBasic() {
  const p = data.value?.person
  if (!p) return
  if (!form.name.trim()) {
    toast.show('姓名不能为空')
    return
  }
  const name = form.name.trim()
  if (persons.value.some((x) => x.id !== p.id && x.name.trim() === name)) {
    toast.show('已存在同名人物')
    return
  }
  const dynasty = form.dynasty.trim()
  const secondaryDynasties = form.secondaryDynasties.filter((d) => d !== dynasty)
  saving.value = true
  try {
    await ensure([dynasty, ...secondaryDynasties])
    await updatePerson(p.id, {
      name,
      dynasty,
      secondary_dynasties: secondaryDynasties,
      identity: form.identities.join('、'),
      birth_year: form.birth === '' ? null : Number(form.birth),
      death_year: form.death === '' ? null : Number(form.death),
      summary: form.summary.trim(),
      color: form.color,
      avatar: form.avatar,
    })
    toast.show('已保存')
    emit('updated')
  } catch (err) {
    console.error('[Chronicle] 保存人物失败', err)
    toast.show('保存失败,请检查后端服务')
  } finally {
    saving.value = false
  }
}

// —— 关系管理(增删) ——
const DIR_ICONS = ['→', '←', '—']
const relLabels = computed(() => {
  const nm = data.value?.person?.name || '此人'
  return [`${nm} → 对方`, `对方 → ${nm}`, '无方向(双向)']
})
function cycleDir(d: number) {
  return (d + 1) % 3
}

const relForm = reactive({ target: 0, label: '', dir: 0 }) // dir: 0=当前→对方 1=对方→当前 2=双向

async function addRelation() {
  const p = data.value?.person
  if (!p) return
  if (!relForm.target) {
    toast.show('请选择关联人物')
    return
  }
  const directed = relForm.dir !== 2
  const fromId = relForm.dir === 1 ? relForm.target : p.id
  const toId = relForm.dir === 1 ? p.id : relForm.target
  try {
    await createRelation({
      from_person_id: fromId,
      to_person_id: toId,
      label: relForm.label.trim() || '关联',
      directed,
    })
    toast.show('已添加关系')
    relForm.target = 0
    relForm.label = ''
    relForm.dir = 0
    emit('updated')
  } catch (err) {
    console.error('[Chronicle] 添加关系失败', err)
    toast.show('添加失败,请检查后端服务')
  }
}

async function delRelation(id: number) {
  if (!(confirmDel.value?.kind === 'rel' && confirmDel.value.id === id)) {
    armConfirm({ kind: 'rel', id })
    return
  }
  confirmDel.value = null
  try {
    await removeRelation(id)
    toast.show('已删除关系')
    emit('updated')
  } catch (err) {
    console.error('[Chronicle] 删除关系失败', err)
    toast.show('删除失败,请检查后端服务')
  }
}

// —— 删除人物(二次确认后级联删除) ——
async function doDelete() {
  const p = data.value?.person
  if (!p) return
  deleting.value = true
  try {
    await removePerson(p.id)
    toast.show('已删除')
    emit('deleted')
  } catch (err) {
    console.error('[Chronicle] 删除人物失败', err)
    toast.show('删除失败,请检查后端服务')
  } finally {
    deleting.value = false
  }
}

// —— 记录批量管理 ——
const selEvents = ref<Set<number>>(new Set())

function toggleEvent(id: number) {
  const s = new Set(selEvents.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selEvents.value = s
}

function allSelected() {
  const evs = data.value?.events ?? []
  return evs.length > 0 && evs.every((e) => selEvents.value.has(e.id))
}

function toggleAll() {
  const evs = data.value?.events ?? []
  selEvents.value = allSelected() ? new Set() : new Set(evs.map((e) => e.id))
}

async function deleteSelected() {
  const ids = [...selEvents.value]
  if (!ids.length) {
    toast.show('请先勾选记录')
    return
  }
  if (confirmDel.value?.kind !== 'batch') {
    armConfirm({ kind: 'batch' })
    return
  }
  confirmDel.value = null
  try {
    await Promise.all(ids.map((id) => removeEvent(id)))
    toast.show(`已删除 ${ids.length} 条记录`)
    selEvents.value = new Set()
    emit('updated')
  } catch (err) {
    console.error('[Chronicle] 批量删除记录失败', err)
    toast.show('删除失败,请检查后端服务')
  }
}

// —— 给 TA 记一条(读模式) ——
const showForm = ref(false)
const submitting = ref(false)
const recForm = reactive({ title: '', year: '', role: '', desc: '' })

async function submitRecord() {
  const d = data.value
  if (!d) return
  if (!recForm.title.trim()) {
    toast.show('请填写事件标题')
    return
  }
  const { year: y, approx } = parseYear(recForm.year)
  submitting.value = true
  try {
    await create({
      title: recForm.title.trim(),
      description: recForm.desc.trim(),
      year_start: y,
      year_end: y,
      year_approx: approx,
      dynasty: d.person.dynasty,
      participants: [{ person_id: d.person.id, role: recForm.role.trim() || '参与' }],
    })
    toast.show('已记录')
    showForm.value = false
    recForm.title = ''
    recForm.year = ''
    recForm.role = ''
    recForm.desc = ''
    emit('recorded')
  } catch (err) {
    console.error('[Chronicle] 记录失败', err)
    toast.show('记录失败,请检查后端服务')
  } finally {
    submitting.value = false
  }
}

// —— 编辑一条记录(编辑模式) ——
const editingEventId = ref<number | null>(null)
const savingEvent = ref(false)
const editForm = reactive({ title: '', year: '', role: '', desc: '' })

function startEditEvent(e: ChronicleEvent) {
  editingEventId.value = e.id
  editForm.title = e.title
  editForm.year = e.year_start != null ? (e.year_approx ? '~' : '') + String(e.year_start) : ''
  editForm.role = roleOf(e.id)
  editForm.desc = e.description || ''
}

function cancelEditEvent() {
  editingEventId.value = null
}

async function saveEditEvent(e: ChronicleEvent) {
  const d = data.value
  if (!d) return
  if (!editForm.title.trim()) {
    toast.show('请填写事件标题')
    return
  }
  const { year: y, approx } = parseYear(editForm.year)
  const pid = d.person.id
  const role = editForm.role.trim() || '参与'
  // 保留其它参与者,仅更新当前人物在该事件中的定位
  const participants = e.participants.map((p) => ({
    person_id: p.person_id,
    role: p.person_id === pid ? role : (p.role || '参与'),
  }))
  savingEvent.value = true
  try {
    await updateEvent(e.id, {
      title: editForm.title.trim(),
      description: editForm.desc.trim(),
      year_start: y,
      year_end: y,
      year_approx: approx,
      participants,
    })
    toast.show('已保存')
    editingEventId.value = null
    emit('updated')
  } catch (err) {
    console.error('[Chronicle] 保存记录失败', err)
    toast.show('保存失败,请检查后端服务')
  } finally {
    savingEvent.value = false
  }
}

// —— 只读展示 ——
const dimmedIds = computed(() => new Set(props.dimmedRelations ?? []))
const relItems = computed(() => {
  const d = data.value
  if (!d) return []
  const pid = d.person.id
  return d.relations.map((r) => {
    const isFrom = r.from_person_id === pid
    const arrow = r.directed ? (isFrom ? '→' : '←') : '↔'
    const other = persons.value.find((p) => p.id === r.other_id)
    const otherColor = r.other_color || (other ? other.color || dynastyColor(other.dynasty) : '#8e8e93')
    return {
      id: r.id,
      label: r.label,
      otherId: r.other_id,
      otherName: r.other_name,
      otherColor,
      arrow,
      dir: `${arrow} ${r.other_name}`,
      directed: r.directed,
      lit: !dimmedIds.value.has(r.id),
    }
  })
})

const birthDeath = computed(() => {
  const p = data.value?.person
  if (!p) return ''
  return yrRange(p.birth_year, p.death_year)
})

// —— 英雄头图:主题色 / 别名 / 姓名排版 ——
const personColor = computed(() => {
  const p = data.value?.person
  return p ? p.color || dynastyColor(p.dynasty) : '#8e8e93'
})
const displayName = computed(() => {
  const n = data.value?.person?.name || ''
  return n.length === 2 ? n.split('').join(' ') : n
})

// 次朝代气泡颜色:按各自朝代色渲染(主朝代气泡仍走 .badge.dyn 的 --dyn)
function subDynastyBadgeStyle(d: string) {
  const c = dynastyColor(d)
  return {
    background: `color-mix(in srgb, ${c} 58%, rgba(0,0,0,.3))`,
    borderColor: `color-mix(in srgb, ${c} 80%, #fff)`,
  }
}

// 身份多值:后端存「、」分隔的字符串,这里拆成数组渲染多个 #身份 气泡
const personIdentities = computed(() =>
  (data.value?.person?.identity || '').split('、').filter(Boolean),
)

function roleOf(eventId: number): string {
  const d = data.value
  if (!d) return ''
  const e = d.events.find((x) => x.id === eventId)
  return e?.participants.find((x) => x.person_id === d.person.id)?.role ?? ''
}

// —— 点击抽屉外部自动收起(仅时间线视图下启用):与下方事件卡片一致 ——
// 拖动时间轴 / 滚轮缩放不触发:拖动累计位移 > 6px 判为拖拽直接跳过;滚轮不产生 mousedown。
// 排除抽屉本体与各类浮层(事件卡片 / 搜索框 / 下拉菜单 / 头像库 / 取色面板 / 添加面板),
// 避免在这些浮层里点击(如切换人物、选朝代)时把抽屉收起又立即重新打开造成闪烁。
const rootEl = ref<HTMLElement | null>(null)
let downX = 0
let downY = 0
let downMoved = 0

function onDocDown(e: MouseEvent) {
  downX = e.clientX
  downY = e.clientY
  downMoved = 0
}
function onDocMove(e: MouseEvent) {
  downMoved += Math.abs(e.clientX - downX) + Math.abs(e.clientY - downY)
  downX = e.clientX
  downY = e.clientY
}
function onDocUp(e: MouseEvent) {
  if (!props.dismissOnOutside || !props.open) return // 未开启或抽屉未打开
  if (downMoved > 6) return // 拖拽 / 滑动,不收起
  const t = e.target as HTMLElement | null
  if (!t || rootEl.value?.contains(t)) return // 点击抽屉内部
  if (t.closest('.evpop, .searchbar, .asel-menu, .avlib, .cp-pop, .addpanel')) return // 浮层内部
  emit('close')
}

onMounted(() => {
  document.addEventListener('mousedown', onDocDown)
  window.addEventListener('mousemove', onDocMove)
  window.addEventListener('mouseup', onDocUp)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocDown)
  window.removeEventListener('mousemove', onDocMove)
  window.removeEventListener('mouseup', onDocUp)
})

</script>

<template>
  <div ref="rootEl" class="drawer" :class="{ show: shown }" :style="{ '--dyn': personColor }">
    <template v-if="data">
      <div class="hero">
        <img v-if="data.person.avatar_url" class="hero-bg" :src="data.person.avatar_url" alt="" />
        <div v-else class="hero-fallback">{{ data.person.name[0] }}</div>
        <div class="top">
          <button v-if="!editing" title="编辑" @click="toggleEdit">✎</button>
        </div>
        <span class="dot" style="width:6px;height:6px;left:150px;top:44px"></span>
        <span class="dot" style="width:4px;height:4px;left:224px;top:30px;opacity:.7"></span>
        <span class="dot" style="width:5px;height:5px;left:84px;top:112px;opacity:.5"></span>
        <div class="ttl">
          <div class="name">{{ displayName }}</div>
          <div class="badges">
            <span class="badge dyn">{{ data.person.dynasty }}</span>
            <span v-for="d in data.person.secondary_dynasties" :key="d" class="badge" :style="subDynastyBadgeStyle(d)">{{ d }}</span>
            <span v-for="id in personIdentities" :key="id" class="badge">{{ id }}</span>
          </div>
          <div class="meta">{{ birthDeath }}　·　关系 {{ data.relations.length }} 条　·　记录 {{ data.events.length }} 条</div>
        </div>
      </div>

      <!-- 编辑模式 -->
      <div class="dr-main">
      <Transition name="view">
      <div v-if="editing" key="edit" class="dr-body">
        <section class="sec">
          <div class="sec-t"><span class="dot"></span>基础信息</div>

        <div class="ap-name-row">
          <div class="ap-field">
            <label>姓名</label>
            <input v-model="form.name" class="ap-inp" :class="{ err: nameDup }" placeholder="姓名" />
            <span v-if="nameDup" class="ap-err">已存在同名人物</span>
          </div>
          <div class="ap-av-wrap">
            <label class="ap-av-lab">头像</label>
            <div class="ap-av-ic">
              <button
                type="button"
                class="ap-av-add"
                :class="{ hasimg: !!avatarPreview, hasname: !avatarPreview && !!form.name.trim() }"
                title="选择头像"
                @click="avOpen = true"
              >
                <img v-if="avatarPreview" :src="avatarPreview" alt="头像" />
                <span v-else-if="form.name.trim()" class="ap-av-char">{{ form.name.trim()[0] }}</span>
                <span v-else class="ap-av-plus">+</span>
              </button>
              <button v-if="form.avatar" type="button" class="ap-av-x" title="移除头像(恢复按名自动匹配)" @click="form.avatar = ''">✕</button>
            </div>
            <input ref="avatarInput" type="file" accept="image/*" class="ap-av-file" @change="onAvatarFile" />
            <AvatarLibrary :open="avOpen" @close="avOpen = false" @select="onPickLibrary" @upload="pickAvatar" />
          </div>
        </div>

        <div class="ap-field">
          <label>身份</label>
          <AppTagInput v-model="form.identities" placeholder="输入身份,回车添加" />
        </div>

        <div class="ap-field">
          <label>主朝代 / 国家</label>
          <div class="ap-dyn-row">
            <AppSelect
              v-model="form.dynasty"
              :options="dynastySelectOptions"
              placeholder="选择朝代 / 国家"
              searchable
              allow-custom
              search-placeholder="搜索或输入朝代 / 国家…"
            />
            <div class="ap-color-wrap">
              <ColorPicker :model-value="pColor" @update:model-value="form.color = $event" />
              <button v-if="form.color" type="button" class="ap-av-x" title="恢复朝代默认色" @click="form.color = ''">✕</button>
            </div>
          </div>
        </div>

        <div class="ap-field">
          <label>次朝代 / 国家 <span class="ap-opt">(可多选)</span></label>
          <AppMultiSelect
            v-model="form.secondaryDynasties"
            :options="secondaryDynastyOptions"
            placeholder="选择次要朝代 / 国家"
            searchable
            allow-custom
            search-placeholder="搜索或输入朝代 / 国家…"
          />
        </div>

        <div class="ap-pair">
          <div class="ap-field">
            <label>生年</label>
            <NumberStepper v-model="form.birth" placeholder="如 –280" />
          </div>
          <div class="ap-field">
            <label>卒年</label>
            <NumberStepper v-model="form.death" placeholder="如 –208" />
          </div>
        </div>

        <div class="ap-field">
          <label>简介</label>
          <textarea v-model="form.summary" class="ap-inp" placeholder="一句话记住 TA…"></textarea>
        </div>

        <div class="f-row">
          <button class="btn primary" :disabled="saving" @click="saveBasic">{{ saving ? '保存中…' : '保存信息' }}</button>
          <button type="button" class="icon-btn" title="重置" @click="resetBasic">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          </button>
        </div>
        </section>

        <section class="sec">
          <div class="sec-t"><span class="dot"></span>关系</div>
          <div v-if="data.relations.length" class="rel-list">
            <div v-for="r in data.relations" :key="'er' + r.id" class="rel-row">
              <span class="rel-chip">
                {{ r.label }} <b>{{ r.directed ? (r.from_person_id === data.person.id ? '→' : '←') : '↔' }} {{ r.other_name }}</b>
              </span>
              <button class="mini-del" :class="{ on: confirmDel?.kind === 'rel' && confirmDel.id === r.id }" @click="delRelation(r.id)">{{ confirmDel?.kind === 'rel' && confirmDel.id === r.id ? '确认?' : '✕' }}</button>
            </div>
          </div>
          <span v-else class="empty">暂无关系</span>

        <div class="ap-field">
          <label>新增关系</label>
          <div class="ap-dir-row">
            <span class="ap-new-chip" title="当前人物">{{ data.person.name[0] }}</span>
            <button type="button" class="ap-dir-btn" :class="{ on: relForm.dir !== 2 }" @click="relForm.dir = cycleDir(relForm.dir)">
              {{ DIR_ICONS[relForm.dir] }}
            </button>
            <AppSelect v-model="relForm.target" :options="personOptions" placeholder="选择人物" />
          </div>
          <span class="ap-dir-lab">{{ relLabels[relForm.dir] }}</span>
        </div>
        <div class="ap-field">
          <input v-model="relForm.label" class="ap-inp" placeholder="如 君臣、同门、父子" />
        </div>
        <button class="btn ghost" @click="addRelation">＋ 添加关系</button>
        </section>

        <section class="sec">
          <div class="sec-t"><span class="dot"></span>记录 ({{ data.events.length }})</div>
        <div v-if="data.events.length" class="rec-batch">
          <div class="rec-batch-bar">
            <label class="ck"><input type="checkbox" class="ckbox" :checked="allSelected()" @change="toggleAll" /> 全选</label>
            <button class="btn sm" :class="confirmDel?.kind === 'batch' ? 'danger' : 'ghost'" :disabled="!selEvents.size" @click="deleteSelected">{{ confirmDel?.kind === 'batch' ? '确认删除?' : '删除选中' }}</button>
          </div>
          <template v-for="e in data.events" :key="'ce' + e.id">
            <div v-if="editingEventId === e.id" class="ev-edit">
              <div class="ap-field">
                <label>事件标题</label>
                <input v-model="editForm.title" class="ap-inp" placeholder="如 长平之战" />
              </div>
              <div class="ap-pair">
                <div class="ap-field">
                  <label>年份(可不填)</label>
                  <input v-model="editForm.year" class="ap-inp" placeholder="如 –260 或 ~-260" />
                </div>
                <div class="ap-field">
                  <label>定位</label>
                  <input v-model="editForm.role" class="ap-inp" placeholder="如 主将" />
                </div>
              </div>
              <div class="ap-field">
                <label>简述</label>
                <textarea v-model="editForm.desc" class="ap-inp" placeholder="发生了什么…"></textarea>
              </div>
              <div class="f-row">
                <button class="btn primary sm" :disabled="savingEvent" @click="saveEditEvent(e)">{{ savingEvent ? '保存中…' : '保存' }}</button>
                <button class="btn ghost sm" @click="cancelEditEvent">取消</button>
              </div>
            </div>
            <div v-else class="rec-ck">
              <input type="checkbox" class="ckbox" :checked="selEvents.has(e.id)" @change="toggleEvent(e.id)" />
              <div class="rec-body">
                <div class="t">{{ e.title }}</div>
                <div class="d">{{ yrRange(e.year_start, e.year_end, e.year_approx) }} · {{ roleOf(e.id) }}</div>
              </div>
              <button type="button" class="mini-edit" title="编辑记录" @click="startEditEvent(e)">✎</button>
            </div>
          </template>
        </div>
        <span v-else class="empty">暂无记录</span>
        </section>
      </div>

      <!-- 只读模式 -->
      <div v-else key="read" class="dr-body">
        <div class="sec-t"><span class="dot"></span>小 传</div>
        <div class="bio">{{ data.person.summary }}</div>

        <div class="sec-t"><span class="dot"></span>关 系 ({{ data.relations.length }})</div>
        <template v-if="relItems.length">
          <div class="rels">
            <div v-for="r in relItems" :key="'r' + r.id" class="rel" :class="{ lit: r.lit }" :style="{ '--rc': r.otherColor }" @click="emit('highlight-relation', r.id)">
              <span class="dot" :title="'查看 ' + r.otherName" @click.stop="emit('select-person', r.otherId)">{{ r.otherName[0] }}</span>
              <span class="nm">{{ r.label }} · {{ r.otherName }}</span>
              <span class="arrow">{{ r.arrow }}</span>
            </div>
          </div>
        </template>
        <span v-else class="empty">暂无关系</span>

        <div class="sec-t"><span class="dot"></span>记 录 ({{ data.events.length }})</div>
        <template v-if="data.events.length">
          <div class="recs">
            <div v-for="e in data.events" :key="'e' + e.id" class="rec" @click="emit('select-event', e.id)">
              <div class="t">{{ e.title }}</div>
              <div class="d">{{ yrRange(e.year_start, e.year_end, e.year_approx) }} · {{ roleOf(e.id) }}</div>
            </div>
          </div>
        </template>
        <span v-else class="empty">暂无记录</span>
      </div>
      </Transition>
      </div>

      <div class="dr-ft">
        <template v-if="editing">
          <div class="f-row">
            <button class="btn primary" @click="editing = false">完成</button>
            <button v-if="!confirmDelete" class="btn danger-ghost" @click="confirmDelete = true">删除人物</button>
            <button v-else class="btn ghost" @click="confirmDelete = false">取消</button>
          </div>
          <div v-if="confirmDelete" class="del-confirm">
            <div class="del-msg">确定删除「{{ data.person.name }}」吗?将同时删除其关联的事件参与和关系。</div>
            <button class="btn danger" :disabled="deleting" @click="doDelete">{{ deleting ? '删除中…' : '确认删除' }}</button>
          </div>
        </template>
        <template v-else-if="!showForm">
          <div class="f-row">
            <button class="btn primary" @click="showForm = true">+ 给 TA 记一条</button>
            <button class="btn ghost" @click="emit('close')">关闭</button>
          </div>
        </template>
        <template v-else>
          <div class="ap-field">
            <label>事件标题</label>
            <input v-model="recForm.title" class="ap-inp" placeholder="如 长平之战" />
          </div>
          <div class="ap-pair">
            <div class="ap-field">
              <label>年份(可不填)</label>
              <input v-model="recForm.year" class="ap-inp" placeholder="如 –260 或 ~-260" />
            </div>
            <div class="ap-field">
              <label>定位</label>
              <input v-model="recForm.role" class="ap-inp" placeholder="如 主将" />
            </div>
          </div>
          <div class="ap-field">
            <label>简述</label>
            <textarea v-model="recForm.desc" class="ap-inp" placeholder="发生了什么…"></textarea>
          </div>
          <div class="f-row">
            <button class="btn primary" :disabled="submitting" @click="submitRecord">{{ submitting ? '保存中…' : '保存' }}</button>
            <button class="btn ghost" @click="showForm = false">取消</button>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>
