<script setup lang="ts">
import type { CustomDynasty, Person } from '~/types/chronicle'
import { DYNASTY_CATALOG, hashColor, dynastyRange, rangeLabel, rangesOverlap, toggleableDynastyBands, parseYear, sanitizeYearEl } from '~/utils/dynasty'

// 全局"朝代/国家"筛选选框:关系网与时间线共用,支持多选打勾(点一下选中,再点取消)。
// 选中朝代颜色数组由父组件持有(v-model),分别驱动关系网的边/节点高亮与时间线的事件过滤。
// 内置目录(默认,不可删除) + 自定义朝代(后端独立管理,支持增删改、可填起止年份,横线分隔)。
// 自定义"带年份"朝代与内置朝代行为一致:有点亮按钮、悬浮显示时间段、可在时间轴排布为分块。
const props = defineProps<{ persons: Person[]; modelValue: string[]; unlit: string[]; mode: 'graph' | 'timeline' }>()
const emit = defineEmits<{
  (e: 'update:modelValue', colors: string[]): void
  (e: 'update:unlit', names: string[]): void
}>()

const { dynasties, create, update, remove } = useDynasties()
const toast = useToast()

const open = ref(false)
const query = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

// 内置图例 = 可点亮/熄灭的朝代分块全集(宏观分块 + 目录细分,含"汉/晋"等仅存在于宏观分块的),按时间排序
const builtinLegend = computed(() => toggleableDynastyBands().map(({ name, color }) => ({ name, color })))
const allLegend = computed(() => [...builtinLegend.value, ...dynasties.value])
const selectedNames = computed(() =>
  allLegend.value.filter((d) => props.modelValue.includes(dynastyColorOf(d))).map((d) => d.name),
)
const triggerLabel = computed(() => {
  const n = selectedNames.value.length
  if (n === 0) return '朝代/国家'
  if (n === 1) return selectedNames.value[0]
  return `已选 ${n} 项`
})
const triggerDot = computed(() => {
  const first = allLegend.value.find((d) => props.modelValue.includes(dynastyColorOf(d)))
  return first ? dynastyColorOf(first) : '#8e8e93'
})

// 下拉搜索:按输入实时过滤(空串显示全部),默认组与自定义组各自过滤。
const q = computed(() => query.value.trim().toLowerCase())
const builtinFiltered = computed(() =>
  q.value ? builtinLegend.value.filter((d) => d.name.toLowerCase().includes(q.value)) : builtinLegend.value,
)
const customFiltered = computed(() =>
  q.value ? dynasties.value.filter((d) => d.name.toLowerCase().includes(q.value)) : dynasties.value,
)

function openMenu() {
  query.value = ''
  adding.value = false
  editingId.value = null
  open.value = true
  nextTick(() => inputEl.value?.focus())
}

function closeMenu() {
  open.value = false
  query.value = ''
  adding.value = false
  editingId.value = null
}

function toggle(color: string) {
  const next = props.modelValue.includes(color)
    ? props.modelValue.filter((c) => c !== color)
    : [...props.modelValue, color]
  emit('update:modelValue', next)
}

function pickAll() {
  emit('update:modelValue', [])
}

function dynastyColorOf(d: { name: string; color: string }): string {
  return d.color || hashColor(d.name)
}

// —— 点亮/熄灭:前面的颜色圆圈 = 按钮区,点击点亮(无勾)则该朝代在时间轴分块 / 关系网中展示,再点熄灭则隐藏 ——
function isUnlit(name: string): boolean {
  return props.unlit.includes(name)
}

// 该朝代是否有可排布的时间区间(决定是否显示点亮按钮:无区间的自定义朝代没有分块,始终展示)
function hasRange(name: string): boolean {
  return !!dynastyRange(name, dynasties.value)
}

// 点亮/熄灭:时间线才做时间重叠检测(同一时间段只展示一个区域,点亮时自动熄灭重叠分块并提醒);
// 关系网与时间无关,直接点亮/熄灭人物标签,不检测重叠、不弹提醒。
function toggleLight(name: string) {
  if (isUnlit(name)) {
    let next = props.unlit.filter((n) => n !== name) // 点亮 name
    if (props.mode === 'timeline') {
      const bands = toggleableDynastyBands(dynasties.value)
      const self = bands.find((b) => b.name === name)
      if (self) {
        const overlaps = bands.filter((b) => b.name !== name && !next.includes(b.name) && rangesOverlap(self, b))
        if (overlaps.length) {
          next = [...next, ...overlaps.map((b) => b.name)]
          toast.show(`同一时间段只能展示一个区域，${overlaps.map((b) => b.name).join('、')} 已不展示`)
        }
      }
    }
    emit('update:unlit', next)
  } else {
    emit('update:unlit', [...props.unlit, name])
  }
}

function lightTitle(name: string): string {
  const rng = rangeLabel(dynastyRange(name, dynasties.value))
  const base = isUnlit(name) ? '点亮' : '熄灭'
  const scope = props.mode === 'graph' ? '关系网中' : '时间轴分块中'
  const act = isUnlit(name) ? '展示' : '隐藏'
  return rng ? `${base}（${rng}）:在${scope}${act}` : `${base}:在${scope}${act}`
}

// —— 悬浮提示:条目上悬浮显示时间段(Teleport 到 body,避免被下拉菜单 overflow 裁剪)——
const tip = ref<{ text: string; x: number; y: number } | null>(null)
function showTip(e: MouseEvent, name: string) {
  const rng = rangeLabel(dynastyRange(name, dynasties.value))
  if (!rng) {
    tip.value = null
    return
  }
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  tip.value = { text: rng, x: rect.right + 10, y: rect.top + rect.height / 2 }
}
function hideTip() {
  tip.value = null
}

// 年份输入解析:复用统一 parseYear,支持 "前221" / "-221" 表公元前、约略 ~ /「约」,空串或非法回 null。
function yearOf(s: string): number | null {
  return parseYear(s).year
}

// —— 添加自定义朝代 ——
const adding = ref(false)
const newName = ref('')
const newColor = ref('')
const newStart = ref('')
const newEnd = ref('')

function startAdd() {
  adding.value = true
  editingId.value = null
  newName.value = ''
  newColor.value = ''
  newStart.value = ''
  newEnd.value = ''
  nextTick(() => addInputEl.value?.focus())
}

// 添加朝代/国家:输入完名字立即提示重名并标红(内置 + 已建自定义)
const newDup = computed(() => {
  const n = newName.value.trim()
  if (!n) return false
  return DYNASTY_CATALOG.some((d) => d.name === n) || dynasties.value.some((d) => d.name === n)
})

async function confirmAdd() {
  const name = newName.value.trim()
  if (!name) return
  if (DYNASTY_CATALOG.some((d) => d.name === name)) {
    toast.show('内置朝代/国家已存在,无需添加')
    return
  }
  if (dynasties.value.some((d) => d.name === name)) {
    toast.show('该朝代/国家已存在')
    return
  }
  try {
    await create({
      name,
      color: newColor.value || hashColor(name),
      start_year: yearOf(newStart.value),
      end_year: yearOf(newEnd.value),
    })
    adding.value = false
  } catch (err: any) {
    toast.show(err?.data?.detail || '添加失败')
  }
}

// —— 编辑 / 删除自定义朝代 ——
const editingId = ref<number | null>(null)
const editName = ref('')
const editColor = ref('')
const editStart = ref('')
const editEnd = ref('')
// 删除二次确认:首击进入待确认,再击才真正删除;3 秒无操作自动复位
const confirmDelId = ref<number | null>(null)
let confirmDelTimer: ReturnType<typeof setTimeout> | null = null

function startEdit(d: CustomDynasty) {
  editingId.value = d.id
  adding.value = false
  editName.value = d.name
  editColor.value = d.color
  editStart.value = d.start_year?.toString() ?? ''
  editEnd.value = d.end_year?.toString() ?? ''
  nextTick(() => editInputEl.value?.focus())
}

async function confirmEdit() {
  const id = editingId.value
  const name = editName.value.trim()
  if (id == null || !name) return
  if (DYNASTY_CATALOG.some((d) => d.name === name)) {
    toast.show('内置朝代/国家名不可用')
    return
  }
  if (dynasties.value.some((d) => d.name === name && d.id !== id)) {
    toast.show('该朝代/国家已存在')
    return
  }
  try {
    await update(id, {
      name,
      color: editColor.value || hashColor(name),
      start_year: yearOf(editStart.value),
      end_year: yearOf(editEnd.value),
    })
    editingId.value = null
  } catch (err: any) {
    toast.show(err?.data?.detail || '保存失败')
  }
}

async function removeDynasty(d: CustomDynasty) {
  if (confirmDelId.value !== d.id) {
    confirmDelId.value = d.id
    if (confirmDelTimer) clearTimeout(confirmDelTimer)
    confirmDelTimer = setTimeout(() => (confirmDelId.value = null), 3000)
    return
  }
  confirmDelId.value = null
  try {
    await remove(d.id)
    // 若当前筛选色里包含被删朝代的颜色,一并剔除
    const c = dynastyColorOf(d)
    if (props.modelValue.includes(c)) emit('update:modelValue', props.modelValue.filter((x) => x !== c))
    // 若该朝代已被熄灭,从熄灭清单里一并移除(避免残留旧名)
    if (props.unlit.includes(d.name)) emit('update:unlit', props.unlit.filter((n) => n !== d.name))
  } catch (err: any) {
    toast.show(err?.data?.detail || '删除失败')
  }
}

// 点击自定义行:编辑态下不触发筛选,避免误收起编辑
function onCustomClick(d: CustomDynasty) {
  if (editingId.value === d.id) return
  toggle(dynastyColorOf(d))
}

const addInputEl = ref<HTMLInputElement | null>(null)
const editInputEl = ref<HTMLInputElement | null>(null)

// 点击选框外部收起
function onDocClick(e: MouseEvent) {
  if (!open.value) return
  const t = e.target as HTMLElement
  if (t.closest('.g-select')) return
  if (t.closest('.cp-pop')) return // 点击取色面板不收起下拉
  closeMenu()
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div class="g-select">
    <button v-if="!open" class="g-trigger" @click.stop="openMenu">
      <i :style="{ background: triggerDot }"></i>
      <span>{{ triggerLabel }}</span>
      <svg class="caret" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m6 9 6 6 6-6" />
      </svg>
    </button>
    <div v-else class="g-trigger g-search">
      <input
        ref="inputEl"
        v-model="query"
        class="dyn-input"
        type="text"
        placeholder="搜索朝代/国家…"
        @keydown.esc="closeMenu"
      />
      <button class="dyn-close" title="收起" @click.stop="closeMenu">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
      </button>
    </div>
    <div v-if="open" class="g-menu">
      <!-- 添加自定义朝代:最上方一行按钮,点击展开输入 -->
      <div v-if="!adding" class="g-add-row">
        <button class="g-add" @click.stop="startAdd">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
          添加朝代/国家
        </button>
      </div>
      <div v-else class="g-edit-col">
        <div class="g-edit-row">
          <ColorPicker small :model-value="newColor || hashColor(newName.trim())" @update:model-value="newColor = $event" />
          <input
            ref="addInputEl"
            v-model="newName"
            class="g-edit-inp"
            :class="{ err: newDup }"
            type="text"
            placeholder="输入朝代/国家名"
            @keydown.enter="confirmAdd"
            @keydown.esc="adding = false"
          />
          <button class="g-row-btn g-ok" title="确认" @click.stop="confirmAdd">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
          </button>
        </div>
        <div class="g-year-row">
          <input v-model="newStart" class="g-year-inp" type="text" placeholder="起始年" @keydown.enter="confirmAdd" @input="newStart = sanitizeYearEl($event)" />
          <input v-model="newEnd" class="g-year-inp" type="text" placeholder="结束年" @keydown.enter="confirmAdd" @input="newEnd = sanitizeYearEl($event)" />
        </div>
        <div class="g-year-hint">- 表公元前(如 -221),~ 表示约</div>
      </div>
      <div v-if="adding && newDup" class="g-dup-warn">已存在同名朝代/国家</div>

      <!-- 全部 -->
      <div class="g-item" :class="{ on: !modelValue.length }" @click.stop="pickAll">
        <i class="all"></i>全部
        <svg class="ck" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
      </div>

      <!-- 内置目录(默认,不可删除) -->
      <div
        v-for="d in builtinFiltered"
        :key="d.name"
        class="g-item"
        :class="{ on: modelValue.includes(d.color) }"
        @click.stop="toggle(d.color)"
        @mouseenter="showTip($event, d.name)"
        @mouseleave="hideTip"
      >
        <button
          class="g-light"
          :class="{ off: isUnlit(d.name) }"
          :style="{ background: d.color, '--lc': d.color }"
          :title="lightTitle(d.name)"
          @click.stop="toggleLight(d.name)"
        ></button>
        <span class="g-name">{{ d.name }}</span>
        <svg class="ck" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
      </div>

      <!-- 横线分隔 + 自定义朝代(可编辑/删除) -->
      <div v-if="dynasties.length" class="g-divider"></div>

      <div
        v-for="d in customFiltered"
        :key="d.id"
        class="g-item g-custom"
        :class="{ on: modelValue.includes(dynastyColorOf(d)) }"
        @click.stop="onCustomClick(d)"
        @mouseenter="showTip($event, d.name)"
        @mouseleave="hideTip"
      >
        <template v-if="editingId === d.id">
          <div class="g-edit-col">
            <div class="g-edit-row">
              <ColorPicker small :model-value="editColor || hashColor(editName.trim())" @update:model-value="editColor = $event" />
              <input
                ref="editInputEl"
                v-model="editName"
                class="g-edit-inp"
                type="text"
                @click.stop
                @keydown.enter="confirmEdit"
                @keydown.esc="editingId = null"
              />
              <button class="g-row-btn g-ok" title="保存" @click.stop="confirmEdit">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
              </button>
            </div>
            <div class="g-year-row">
              <input v-model="editStart" class="g-year-inp" type="text" placeholder="起始年" @keydown.enter="confirmEdit" @input="editStart = sanitizeYearEl($event)" />
              <input v-model="editEnd" class="g-year-inp" type="text" placeholder="结束年" @keydown.enter="confirmEdit" @input="editEnd = sanitizeYearEl($event)" />
            </div>
            <div class="g-year-hint">- 表公元前(如 -221),~ 表示约</div>
          </div>
        </template>
        <template v-else>
          <button
            v-if="hasRange(d.name) || mode === 'graph'"
            class="g-light"
            :class="{ off: isUnlit(d.name) }"
            :style="{ background: dynastyColorOf(d), '--lc': dynastyColorOf(d) }"
            :title="lightTitle(d.name)"
            @click.stop="toggleLight(d.name)"
          ></button>
          <span v-else class="g-swatch" :style="{ background: dynastyColorOf(d) }" :title="d.name"></span>
          <span class="g-name">{{ d.name }}</span>
          <button class="g-row-btn" title="编辑" @click.stop="startEdit(d)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 3 22l1.5-4.5Z" /></svg>
          </button>
          <button class="g-row-btn g-del" :class="{ on: confirmDelId === d.id }" :title="confirmDelId === d.id ? '再次点击确认删除' : '删除'" @click.stop="removeDynasty(d)">
            <template v-if="confirmDelId === d.id">确认?</template>
            <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
          <svg class="ck" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
        </template>
      </div>

      <div v-if="builtinFiltered.length === 0 && customFiltered.length === 0 && !adding" class="g-empty">无匹配朝代/国家</div>
    </div>
  </div>
  <Teleport to="body">
    <Transition name="gtip">
      <div v-if="tip" class="g-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">{{ tip.text }}</div>
    </Transition>
  </Teleport>
</template>
