<script setup lang="ts">
// 项目内置多选下拉选框:收起态在触发框内显示已选气泡(带色点 + ✕ 可移除),
// 打开态列表每项带勾选框可切换,支持搜索过滤;allowCustom 允许直接输入不在列表里的自定义值。
// 复用 AppSelect 的 .asel-* 样式体系。
import type { SelectOption } from '~/types/chronicle'

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    options: SelectOption[]
    placeholder?: string
    searchable?: boolean
    allowCustom?: boolean
    searchPlaceholder?: string
  }>(),
  { modelValue: () => [], placeholder: '请选择', searchable: true, allowCustom: false, searchPlaceholder: '搜索…' },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: string[]): void
}>()

const open = ref(false)
const rootEl = ref<HTMLElement | null>(null)
const triggerEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const menuStyle = ref<Record<string, string>>({})
const query = ref('')

// 已选项的展示信息:列表里的项用其 label/color;自定义值(不在列表)用值本身显示
const selectedItems = computed(() =>
  props.modelValue.map((v) => {
    const o = props.options.find((opt) => String(opt.value) === v)
    return o ? { value: v, label: o.label, color: o.color } : { value: v, label: v, color: undefined }
  }),
)

const filteredOptions = computed<SelectOption[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) => o.label.toLowerCase().includes(q))
})

// 可提交的自定义值:允许自定义、输入非空、且与现有选项无完全一致
const customEntry = computed(() => {
  if (!props.allowCustom) return ''
  const q = query.value.trim()
  if (!q) return ''
  const exact = props.options.some((o) => String(o.label) === q || String(o.value) === q)
  return exact ? '' : q
})

function isSelected(o: SelectOption): boolean {
  return props.modelValue.includes(String(o.value))
}

function openMenu() {
  open.value = true
  query.value = ''
  position()
  if (props.searchable) nextTick(() => inputEl.value?.focus())
}

function close() {
  open.value = false
  query.value = ''
}

function onTriggerClick() {
  if (open.value) {
    if (!props.searchable) close()
    return
  }
  openMenu()
}

function toggle(o: SelectOption) {
  const v = String(o.value)
  const next = new Set(props.modelValue)
  if (next.has(v)) next.delete(v)
  else next.add(v)
  emit('update:modelValue', [...next])
}

function remove(v: string) {
  emit('update:modelValue', props.modelValue.filter((x) => x !== v))
}

function commitCustom() {
  const v = customEntry.value
  if (!v) return
  if (!props.modelValue.includes(v)) {
    emit('update:modelValue', [...props.modelValue, v])
  }
  query.value = ''
  if (props.searchable) nextTick(() => inputEl.value?.focus())
}

function position() {
  const rect = triggerEl.value?.getBoundingClientRect()
  if (!rect) return
  const maxH = 320
  const spaceBelow = window.innerHeight - rect.bottom - 8
  const spaceAbove = rect.top - 8
  let top = rect.bottom + 6
  let maxHeight = maxH
  if (spaceBelow < maxH && spaceAbove > spaceBelow) {
    top = rect.top - 6 - Math.min(maxH, spaceAbove)
    maxHeight = Math.min(maxH, spaceAbove)
  } else {
    maxHeight = Math.min(maxH, spaceBelow)
  }
  menuStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    maxHeight: `${maxHeight}px`,
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
    return
  }
  if (e.key !== 'Enter') return
  e.preventDefault()
  if (customEntry.value) commitCustom()
}

function onDocClick(e: MouseEvent) {
  if (open.value && !rootEl.value?.contains(e.target as Node)) close()
}

function onScroll(e: Event) {
  const t = e.target as Node
  if (menuEl.value && menuEl.value.contains(t)) return
  if (open.value) close()
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  window.addEventListener('scroll', onScroll, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('scroll', onScroll, true)
})
</script>

<template>
  <div ref="rootEl" class="asel">
    <div
      ref="triggerEl"
      class="asel-trigger asel-multi"
      :class="{ open, search: open && searchable }"
      role="button"
      tabindex="0"
      @click.stop="onTriggerClick"
    >
      <svg v-if="open && searchable" class="asel-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>

      <input
        v-if="open && searchable"
        ref="inputEl"
        v-model="query"
        class="asel-input"
        type="text"
        :placeholder="searchPlaceholder"
        @keydown="onKeydown"
      />

      <div v-else class="asel-chips">
        <span v-for="o in selectedItems" :key="o.value" class="asel-chip">
          <i v-if="o.color" class="asel-chip-dot" :style="{ background: o.color }"></i>
          <span class="asel-chip-lab">{{ o.label }}</span>
          <button type="button" class="asel-chip-x" title="移除" @click.stop="remove(String(o.value))">✕</button>
        </span>
        <span v-if="!selectedItems.length" class="asel-val ph">{{ placeholder }}</span>
      </div>

      <button v-if="open && searchable" type="button" class="asel-close" title="收起" @click.stop="close">✕</button>
      <svg v-else class="asel-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
    </div>

    <Teleport to="body">
      <div v-if="open" ref="menuEl" class="asel-menu" :style="menuStyle">
        <button
          v-for="o in filteredOptions"
          :key="o.value"
          type="button"
          class="asel-opt"
          :class="{ on: isSelected(o) }"
          @click="toggle(o)"
        >
          <i v-if="o.color" class="asel-dot" :style="{ background: o.color }"></i>
          <span class="asel-opt-lab">{{ o.label }}</span>
          <svg v-if="isSelected(o)" class="asel-ck" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 13 4 4L19 7" /></svg>
        </button>
        <button v-if="customEntry" type="button" class="asel-opt asel-custom" @click="commitCustom">
          <span class="asel-custom-lab">使用「{{ customEntry }}」</span>
        </button>
        <div v-if="!filteredOptions.length && !customEntry" class="asel-empty">无匹配</div>
      </div>
    </Teleport>
  </div>
</template>
