<script setup lang="ts">
import type { ChronicleEvent } from '~/types/chronicle'
import { dynastyColor, yrRange } from '~/utils/dynasty'

const props = defineProps<{ event: ChronicleEvent | null }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select-person', id: number): void
}>()

// 实际渲染的内容与弹层显隐:切换事件时整个弹层先退出再进入
const shown = ref(false)
const display = ref<ChronicleEvent | null>(null)

watch(
  () => props.event,
  (ev) => {
    if (ev) {
      if (shown.value) {
        // 已显示状态下切换事件:先退出,内容更新后再进入
        shown.value = false
        setTimeout(() => {
          if (!props.event) return
          display.value = props.event
          shown.value = true
        }, 240)
      } else {
        display.value = ev
        shown.value = true
      }
    } else {
      shown.value = false // 关闭:滑出,display 保留
    }
  },
)

function goPerson(id: number) {
  // 点击人物气泡:打开对应人物抽屉,但不关闭事件卡片
  emit('select-person', id)
}

// 点击页面其它地方自动收缩(仅"点击"触发;拖移/滑动时间轴不收缩)
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
  if (downMoved > 6) return // 拖移/滑动,不收缩
  if (!props.event) return // 未打开,不处理
  const t = e.target as HTMLElement | null
  if (!t || rootEl.value?.contains(t)) return // 点击弹层内部
  if (t.closest('.tl-ev')) return // 点击事件卡片:切换到另一事件,不收缩
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
  <div class="evpop" ref="rootEl" :class="{ show: shown }">
    <template v-if="display">
      <div class="hd">
        <h3>{{ display.title }}</h3>
        <span class="yr">{{ yrRange(display.year_start, display.year_end, display.year_approx) + (display.dynasty ? ' · ' + display.dynasty : '') }}</span>
        <button class="x" @click="emit('close')">✕</button>
      </div>
      <p>{{ display.description }}</p>
      <div class="ps">
        <span
          v-for="x in display.participants"
          :key="x.person_id"
          class="chip-p"
          @click="goPerson(x.person_id)"
        >
          <span class="ma" :style="{ background: x.color || dynastyColor(x.dynasty) }">{{ x.name[0] }}</span>{{ x.name }}
          <span class="role">{{ x.role }}</span>
        </span>
      </div>
    </template>
  </div>
</template>
