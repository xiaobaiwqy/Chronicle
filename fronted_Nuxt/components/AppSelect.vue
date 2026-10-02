<script setup lang="ts">
// 项目内置统一下拉选框:胶囊触发框 + 悬浮菜单(Teleport 到 body,避免被滚动容器裁剪)。
// 支持两种增强:
//  - searchable:打开时胶囊变为搜索输入框,边输入边筛选;
//  - allowCustom:允许不选列表,直接输入自定义值(如自定义朝代)。
import type { SelectOption } from '~/types/chronicle'

const props = withDefaults(
  defineProps<{
    modelValue: number | string
    options: SelectOption[]
    placeholder?: string
    searchable?: boolean
    allowCustom?: boolean
    searchPlaceholder?: string
  }>(),
  { placeholder: '请选择', searchable: false, allowCustom: false, searchPlaceholder: '搜索…' },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: number | string): void
}>()

const open = ref(false)
const rootEl = ref<HTMLElement | null>(null)
const triggerEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const menuStyle = ref<Record<string, string>>({})
const query = ref('')

const selected = computed(() => props.options.find((o) => o.value === props.modelValue))
// 显示文案:优先选项;若为自定义字符串(不在选项里),直接显示该值
const displayLabel = computed(() => {
  if (selected.value) return selected.value.label
  if (typeof props.modelValue === 'string' && props.modelValue !== '') return props.modelValue
  return ''
})
const hasValue = computed(() => !!displayLabel.value)

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

function position() {
  const rect = triggerEl.value?.getBoundingClientRect()
  if (!rect) return
  const maxH = 320
  const spaceBelow = window.innerHeight - rect.bottom - 8
  const spaceAbove = rect.top - 8
  let top = rect.bottom + 6
  let maxHeight = maxH
  if (spaceBelow < maxH && spaceAbove > spaceBelow) {
    // 下方空间不足且上方更充裕时,向上弹出
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

function pick(v: number | string) {
  emit('update:modelValue', v)
  close()
}

function commitCustom() {
  if (customEntry.value) {
    emit('update:modelValue', customEntry.value)
    close()
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
    return
  }
  if (e.key !== 'Enter') return
  e.preventDefault()
  if (customEntry.value) {
    commitCustom()
    return
  }
  const first = filteredOptions.value[0]
  if (first) pick(first.value)
}

function onDocClick(e: MouseEvent) {
  if (open.value && !rootEl.value?.contains(e.target as Node)) close()
}

function onScroll(e: Event) {
  // 菜单内部滚动时保持打开(菜单内需可滑动);只有外部容器滚动才收起,避免悬浮菜单与触发框错位
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
      class="asel-trigger"
      :class="{ open, search: open && searchable }"
      role="button"
      tabindex="0"
      @click.stop="onTriggerClick"
    >
      <svg v-if="open && searchable" class="asel-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <i v-else-if="selected?.color" class="asel-dot" :style="{ background: selected.color }"></i>

      <input
        v-if="open && searchable"
        ref="inputEl"
        v-model="query"
        class="asel-input"
        type="text"
        :placeholder="searchPlaceholder"
        @keydown="onKeydown"
      />
      <span v-else class="asel-val" :class="{ ph: !hasValue }">{{ displayLabel || placeholder }}</span>

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
          :class="{ on: o.value === modelValue }"
          @click="pick(o.value)"
        >
          <i v-if="o.color" class="asel-dot" :style="{ background: o.color }"></i>
          <span class="asel-opt-lab">{{ o.label }}</span>
          <svg v-if="o.value === modelValue" class="asel-ck" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 13 4 4L19 7" /></svg>
        </button>
        <button v-if="customEntry" type="button" class="asel-opt asel-custom" @click="commitCustom">
          <span class="asel-custom-lab">使用「{{ customEntry }}」</span>
        </button>
        <div v-if="!filteredOptions.length && !customEntry" class="asel-empty">无匹配</div>
      </div>
    </Teleport>
  </div>
</template>
