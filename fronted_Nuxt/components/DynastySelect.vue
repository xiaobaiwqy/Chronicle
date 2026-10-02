<script setup lang="ts">
import type { Person } from '~/types/chronicle'
import { DYNASTY_CATALOG, hashColor } from '~/utils/dynasty'

// 全局"朝代/国家"筛选选框:关系网与时间线共用。选中朝代颜色由父组件持有(v-model),
// 分别驱动关系网的边/节点高亮与时间线的事件过滤。
// 内置目录(默认,不可删除) + 自定义朝代(后端独立管理,支持增删改,横线分隔)。
const props = defineProps<{ persons: Person[]; modelValue: string | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', color: string | null): void }>()

const { dynasties, create, update, remove } = useDynasties()
const toast = useToast()

const open = ref(false)
const query = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

const builtinLegend = computed(() => DYNASTY_CATALOG.map((d) => ({ name: d.name, color: d.color })))
const allLegend = computed(() => [...builtinLegend.value, ...dynasties.value])
const selectedName = computed(() => allLegend.value.find((d) => d.color === props.modelValue)?.name ?? null)

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

function pick(color: string | null) {
  emit('update:modelValue', color)
  closeMenu()
}

// —— 添加自定义朝代 ——
const adding = ref(false)
const newName = ref('')
const newColor = ref('')

function startAdd() {
  adding.value = true
  editingId.value = null
  newName.value = ''
  newColor.value = ''
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
    await create({ name, color: newColor.value || hashColor(name) })
    adding.value = false
  } catch (err: any) {
    toast.show(err?.data?.detail || '添加失败')
  }
}

// —— 编辑 / 删除自定义朝代 ——
const editingId = ref<number | null>(null)
const editName = ref('')
const editColor = ref('')

function startEdit(d: { id: number; name: string; color: string }) {
  editingId.value = d.id
  adding.value = false
  editName.value = d.name
  editColor.value = d.color
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
    await update(id, { name, color: editColor.value || hashColor(name) })
    editingId.value = null
  } catch (err: any) {
    toast.show(err?.data?.detail || '保存失败')
  }
}

async function removeDynasty(d: { id: number; name: string }) {
  try {
    await remove(d.id)
    // 若当前筛选色恰好是被删朝代的颜色,一并清除筛选
    if (props.modelValue && dynastyColorOf(d) === props.modelValue) emit('update:modelValue', null)
  } catch (err: any) {
    toast.show(err?.data?.detail || '删除失败')
  }
}

function dynastyColorOf(d: { name: string; color: string }): string {
  return d.color || hashColor(d.name)
}

// 点击自定义行:编辑态下不触发筛选,避免误收起编辑
function onCustomClick(d: { id: number; name: string; color: string }) {
  if (editingId.value === d.id) return
  pick(dynastyColorOf(d))
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
      <i :style="{ background: modelValue || '#8e8e93' }"></i>
      <span>{{ selectedName || '朝代/国家' }}</span>
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
      <div v-else class="g-edit-row">
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
      <div v-if="adding && newDup" class="g-dup-warn">已存在同名朝代/国家</div>

      <!-- 全部 -->
      <div class="g-item" :class="{ on: !modelValue }" @click.stop="pick(null)">
        <i class="all"></i>全部
        <svg class="ck" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
      </div>

      <!-- 内置目录(默认,不可删除) -->
      <div
        v-for="d in builtinFiltered"
        :key="d.name"
        class="g-item"
        :class="{ on: modelValue === d.color }"
        @click.stop="pick(d.color)"
      >
        <i :style="{ background: d.color }"></i>{{ d.name }}
        <svg class="ck" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
      </div>

      <!-- 横线分隔 + 自定义朝代(可编辑/删除) -->
      <div v-if="dynasties.length" class="g-divider"></div>

      <div
        v-for="d in customFiltered"
        :key="d.id"
        class="g-item g-custom"
        :class="{ on: modelValue === dynastyColorOf(d) }"
        @click.stop="onCustomClick(d)"
      >
        <template v-if="editingId === d.id">
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
        </template>
        <template v-else>
          <i :style="{ background: dynastyColorOf(d) }"></i>
          <span class="g-name">{{ d.name }}</span>
          <button class="g-row-btn" title="编辑" @click.stop="startEdit(d)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 3 22l1.5-4.5Z" /></svg>
          </button>
          <button class="g-row-btn g-del" title="删除" @click.stop="removeDynasty(d)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </template>
      </div>

      <div v-if="builtinFiltered.length === 0 && customFiltered.length === 0 && !adding" class="g-empty">无匹配朝代/国家</div>
    </div>
  </div>
</template>
