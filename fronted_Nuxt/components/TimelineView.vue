<script setup lang="ts">
import type { ChronicleEvent } from '~/types/chronicle'
import { TIMELINE_BANDS, dynastyColor, yrFmt, yrRange } from '~/utils/dynasty'

const props = defineProps<{ events: ChronicleEvent[]; selectedEventId: number | null; active: boolean; dynastyFilter: string | null }>()
const emit = defineEmits<{ (e: 'select-event', id: number): void }>()

// —— 非均匀时间轴参数 ——
// 分块宽度 = max(名称兜底, (年份跨度×K_SPAN + 事件数×K_EVENT) × zoom);刻度跟随朝代起始年与事件年份。
const K_SPAN = 0.22 // 每单位年份的基础像素(保留大致时间比例)
const K_EVENT = 36 // 每个事件额外分配的像素
const NAME_W = 30 // 与 .dyn-name 字号一致,按朝代名长度兜底最小宽度
const NAME_PAD = 24 // 名称两侧留白
const PAD = 40 // 画布左右留白
const TICK_GAP = 56 // 相邻刻度最小像素间距(低于则合并)
const CARD_W = 150 // .tl-ev 卡片宽度(用于防重叠)
const HALF = CARD_W / 2
const CARD_GAP = 6 // 相邻卡片最小间隙
const ZOOM_MIN = 0.25

const wrapEl = ref<HTMLElement | null>(null)
const H = ref(500)
const zoom = ref(1)
const scrollLeft = ref(0)
const viewW = ref(0)
function syncScroll() {
  if (!wrapEl.value) return
  scrollLeft.value = wrapEl.value.scrollLeft
  viewW.value = wrapEl.value.clientWidth
}

// 事件按朝代筛选(左上角"朝代/国家"选框):未选时显示全部。
// 事件按是否有年份分两组:有年份的进时间轴,无年份的集中到右侧"不详"区块。
type DatedEvent = ChronicleEvent & { year_start: number }
function isDated(e: ChronicleEvent): e is DatedEvent {
  return e.year_start != null
}
const datedEvents = computed(() => props.events.filter(isDated))
const undatedEvents = computed(() => props.events.filter((e) => !isDated(e)))
const filteredDated = computed(() => {
  if (!props.dynastyFilter) return datedEvents.value
  return datedEvents.value.filter((e) => dynastyColor(e.dynasty) === props.dynastyFilter)
})
const filteredUndated = computed(() => {
  if (!props.dynastyFilter) return undatedEvents.value
  return undatedEvents.value.filter((e) => dynastyColor(e.dynasty) === props.dynastyFilter)
})

// 自定义朝代分块:事件年份落在预设分块之外时,按朝代聚合生成新分块(用户新增事件自动扩展时间线)
const customBands = computed(() => {
  const groups = new Map<string, { min: number; max: number }>()
  for (const e of datedEvents.value) {
    const y = e.year_start
    if (TIMELINE_BANDS.some((b) => y >= b.s && y <= b.e)) continue
    const lo = Math.min(y, e.year_end ?? y)
    const hi = Math.max(y, e.year_end ?? y)
    const g = groups.get(e.dynasty)
    if (g) {
      g.min = Math.min(g.min, lo)
      g.max = Math.max(g.max, hi)
    } else {
      groups.set(e.dynasty, { min: lo, max: hi })
    }
  }
  return [...groups.entries()].map(([name, r]) => ({
    name: name || '未知',
    color: dynastyColor(name),
    s: r.min,
    e: r.max,
  }))
})

// 全部分块(预设 + 自定义),按起始年份排序
const allBands = computed(() =>
  [...TIMELINE_BANDS.map((b) => ({ ...b })), ...customBands.value].sort((a, b) => a.s - b.s),
)

// 布局:用给定 zoom 计算各分块宽度并累积起始像素(分块宽度 = max(名称兜底, (年份跨度×K_SPAN + 事件数×K_EVENT) × zoom))
function computeLayout(z: number) {
  let x = PAD
  const items = allBands.value.map((b) => {
    const span = Math.max(1, b.e - b.s)
    const evs = datedEvents.value.filter((e) => e.year_start >= b.s && e.year_start <= b.e).length
    const base = span * K_SPAN + evs * K_EVENT
    const w = Math.max(NAME_W * b.name.length + NAME_PAD, base * z)
    const seg = { ...b, w, x0: x, x1: x + w, count: evs }
    x += w
    return seg
  })
  return { items, totalW: x + PAD }
}

const layout = computed(() => computeLayout(zoom.value))

// —— 无年份事件:"不详"区块固定在时间轴最右端 ——
const undatedBand = computed(() => {
  const count = filteredUndated.value.length
  if (!count) return { x0: 0, x1: 0, w: 0, count }
  const items = layout.value.items
  const x0 = (items.length ? items[items.length - 1].x1 : PAD) + 40
  const w = Math.max(NAME_W * 2 + NAME_PAD, count * (CARD_W + CARD_GAP) + PAD)
  return { x0, x1: x0 + w, w, count }
})
const totalW = computed(() => Math.max(layout.value.totalW, undatedBand.value.x1 + PAD))

const undatedCards = computed(() => {
  const band = undatedBand.value
  if (!band.count) return []
  const AXIS = H.value / 2
  return filteredUndated.value.map((e, i) => {
    const x = band.x0 + PAD / 2 + i * (CARD_W + CARD_GAP)
    const h = 50 + (i % 3) * 36
    const above = i % 2 === 0
    return { e, color: dynastyColor(e.dynasty), above, h, x, top: above ? AXIS - h - 62 : AXIS + 13 }
  })
})

// 视口内可见的分块数:放大到只剩一个朝代块时,关闭悬浮发光
const singleBand = computed(() => {
  const x0 = scrollLeft.value
  const x1 = scrollLeft.value + (viewW.value || 1)
  return layout.value.items.filter((d) => d.x1 > x0 && d.x0 < x1).length <= 1
})

// 年份 -> 像素:分块内按年份线性,分块间按累积偏移;超出范围线性外推
function xIn(y: number, items: { s: number; e: number; w: number; x0: number; x1: number }[]): number {
  if (!items.length) return PAD
  const first = items[0]
  if (y < first.s) return first.x0 + (y - first.s) * K_SPAN
  for (const seg of items) {
    if (y >= seg.s && y <= seg.e) {
      return seg.x0 + ((y - seg.s) / (seg.e - seg.s)) * seg.w
    }
  }
  const last = items[items.length - 1]
  return last.x1 + (y - last.e) * K_SPAN
}

function X(y: number): number {
  return xIn(y, layout.value.items)
}

// 非均匀刻度:每个朝代的起始年 + 时间线末尾 + 事件年份,按像素间距去重
const ticks = computed(() => {
  const years = new Set<number>()
  const items = layout.value.items
  for (const seg of items) years.add(seg.s)
  if (items.length) years.add(items[items.length - 1].e)
  for (const e of filteredDated.value) years.add(e.year_start)
  const sorted = [...years].sort((a, b) => a - b)
  const out: number[] = []
  for (const y of sorted) {
    if (out.length && Math.abs(X(y) - X(out[out.length - 1])) < TICK_GAP) continue
    out.push(y)
  }
  return out
})

// 事件卡片:按年份排序,上下两 lane 贪心防重叠——放不下的隐藏(LOD)。
// 放大时分块拉宽、间距变大,更多事件能放下,从而展示更多细节事件。
const cards = computed(() => {
  const sorted = [...filteredDated.value].sort((a, b) => a.year_start - b.year_start)
  const AXIS = H.value / 2
  let lastAbove = -Infinity
  let lastBelow = -Infinity
  let placed = 0
  const out: { e: ChronicleEvent; color: string; above: boolean; h: number; x: number; top: number }[] = []
  for (const e of sorted) {
    const x = X(e.year_start)
    const h = 50 + (placed % 3) * 36
    if (x - HALF >= lastAbove + CARD_GAP) {
      lastAbove = x + HALF
      out.push({ e, color: dynastyColor(e.dynasty), above: true, h, x, top: AXIS - h - 62 })
      placed++
    } else if (x - HALF >= lastBelow + CARD_GAP) {
      lastBelow = x + HALF
      out.push({ e, color: dynastyColor(e.dynasty), above: false, h, x, top: AXIS + 13 })
      placed++
    }
  }
  return out
})

// 让当前筛选下所有事件卡片都能放下所需的最小 zoom(动态上限依据)。
// 逐次翻倍扩张再二分收敛;同年事件上下两 lane 各最多一个,极端密集时上限随间距成比例拉高。
const fitAllZoom = computed(() => {
  const sorted = [...filteredDated.value].sort((a, b) => a.year_start - b.year_start)
  const total = sorted.length
  if (total < 2) return 1
  const canAll = (z: number) => {
    const { items } = computeLayout(z)
    let lastAbove = -Infinity
    let lastBelow = -Infinity
    let placed = 0
    for (const e of sorted) {
      const x = xIn(e.year_start, items)
      if (x - HALF >= lastAbove + CARD_GAP) {
        lastAbove = x + HALF
        placed++
      } else if (x - HALF >= lastBelow + CARD_GAP) {
        lastBelow = x + HALF
        placed++
      }
    }
    return placed >= total
  }
  let lo = ZOOM_MIN
  let hi = 2
  let guard = 0
  while (!canAll(hi) && guard++ < 60) hi *= 2
  if (!canAll(hi)) return hi // 横向无法完全铺开时给一个很大的上限,避免死循环
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2
    if (canAll(mid)) hi = mid
    else lo = mid
  }
  return hi
})

// 动态放大上限:一直放大到所有事件可见为止(略留余量),替代固定上限
const zoomMax = computed(() => Math.max(6, fitAllZoom.value * 1.2))

// —— 拖拽横向滚动 ——
let down = false
let sx = 0
let sl = 0
let dragMoved = 0

function onDown(e: MouseEvent) {
  animId++ // 打断正在进行的聚焦动画
  down = true
  sx = e.clientX
  sl = wrapEl.value!.scrollLeft
  dragMoved = 0
  wrapEl.value!.style.cursor = 'grabbing'
}

function onMove(e: MouseEvent) {
  if (!down || !wrapEl.value) return
  const dx = e.clientX - sx
  dragMoved += Math.abs(dx)
  wrapEl.value.scrollLeft = sl - dx
}

function onUp() {
  down = false
  if (wrapEl.value) wrapEl.value.style.cursor = 'grab'
}

function onCard(id: number) {
  if (dragMoved > 6) return
  emit('select-event', id)
}

// —— 滚轮缩放(以鼠标为锚点) ——
function onWheel(e: WheelEvent) {
  e.preventDefault()
  animId++
  const wrap = wrapEl.value!
  const rect = wrap.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const worldX = wrap.scrollLeft + mouseX
  const factor = Math.exp(-e.deltaY * 0.0015)
  const newZoom = Math.min(zoomMax.value, Math.max(ZOOM_MIN, zoom.value * factor))
  const ratio = newZoom / zoom.value
  zoom.value = newZoom
  wrap.scrollLeft = worldX * ratio - mouseX
}

// —— 分块点击聚焦(丝滑缩放+滚动) ——
let animId = 0
let focusedS: number | null = null

function animateTo(targetZoom: number, scrollAt: () => number) {
  const id = ++animId
  const startZoom = zoom.value
  const t0 = performance.now()
  const DUR = 420
  const step = (now: number) => {
    if (id !== animId) return
    const t = Math.min(1, (now - t0) / DUR)
    const e = 1 - Math.pow(1 - t, 3)
    zoom.value = startZoom + (targetZoom - startZoom) * e
    wrapEl.value!.scrollLeft = scrollAt()
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function focusBand(seg: { s: number; e: number; w: number }) {
  if (dragMoved > 6) return
  const vw = wrapEl.value!.clientWidth
  if (focusedS === seg.s) {
    // 再次点击:恢复全局视图(居中整条时间线),不裁剪任何区域
    focusedS = null
    animateTo(1, () => (totalW.value - vw) / 2)
  } else {
    focusedS = seg.s
    const baseW = seg.w / zoom.value
    const targetZoom = Math.min(zoomMax.value, Math.max(ZOOM_MIN, vw / baseW))
    animateTo(targetZoom, () => (X(seg.s) + X(seg.e)) / 2 - vw / 2)
  }
}

// 搜索框选中事件:平滑放大到所有事件可见并滚动居中到该事件(高亮由 selectedEventId 驱动)
function focusEvent(id: number) {
  if (!props.active || !wrapEl.value) return
  const e = props.events.find((x) => x.id === id)
  if (!e) return
  const vw = wrapEl.value.clientWidth
  const targetZoom = Math.min(zoomMax.value, Math.max(zoom.value, fitAllZoom.value))
  if (e.year_start == null) {
    animateTo(targetZoom, () => undatedBand.value.x0 - vw / 3)
  } else {
    animateTo(targetZoom, () => X(e.year_start) - vw / 2)
  }
}

defineExpose({ focusEvent })

function onResize() {
  if (!props.active) return
  H.value = wrapEl.value?.clientHeight || 500
  syncScroll()
}

let scrolledOnce = false

onMounted(() => {
  wrapEl.value!.addEventListener('mousedown', onDown)
  wrapEl.value!.addEventListener('wheel', onWheel, { passive: false })
  wrapEl.value!.addEventListener('scroll', syncScroll)
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
  window.addEventListener('resize', onResize)
})

// 切回时间线时重测高度;初始滚动到最早事件(无事件则回到最左),只设置一次
watch(
  () => props.active,
  async (on) => {
    if (!on) return
    await nextTick()
    H.value = wrapEl.value?.clientHeight || 500
    syncScroll()
    if (!scrolledOnce && wrapEl.value) {
      const first = [...datedEvents.value].sort((a, b) => a.year_start - b.year_start)[0]
      if (first) wrapEl.value.scrollLeft = X(first.year_start) - 200
      else if (undatedBand.value.count) wrapEl.value.scrollLeft = undatedBand.value.x0 - 100
      else wrapEl.value.scrollLeft = 0
      scrolledOnce = true
      syncScroll()
    }
  },
)

onBeforeUnmount(() => {
  wrapEl.value?.removeEventListener('scroll', syncScroll)
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div class="tl-wrap" :class="{ single: singleBand }" ref="wrapEl">
    <div class="tl-canvas" :style="{ width: totalW + 'px' }">
      <div
        v-for="d in layout.items"
        :key="d.name + d.s"
        class="dyn-band"
        :style="{ left: d.x0 + 'px', width: d.w + 'px', '--dc': d.color }"
        @click="focusBand(d)"
      >
        <div class="dyn-lab"><span class="dyn-name">{{ d.name }}</span><span class="dyn-yrs">{{ yrFmt(d.s) }}–{{ yrFmt(d.e) }}</span><span class="dyn-cnt">当前记录 {{ d.count }} 事件</span></div>
      </div>
      <div
        v-if="undatedBand.count"
        class="dyn-band"
        :style="{ left: undatedBand.x0 + 'px', width: undatedBand.w + 'px', '--dc': '#8e8e93' }"
      >
        <div class="dyn-lab"><span class="dyn-name">不详</span><span class="dyn-yrs">未定年</span><span class="dyn-cnt">当前记录 {{ undatedBand.count }} 事件</span></div>
      </div>
      <div class="tl-axis"></div>
      <div v-for="y in ticks" :key="y" class="tl-tick" :style="{ left: X(y) + 'px' }">
        <span>{{ yrFmt(y) }}</span>
      </div>
      <div
        v-for="c in cards"
        :key="c.e.id"
        class="tl-ev"
        :class="{ sel: c.e.id === selectedEventId }"
        :style="{ left: c.x + 'px', top: c.top + 'px', '--dc': c.color }"
        @click.stop="onCard(c.e.id)"
      >
        <template v-if="c.above">
          <div class="bx">
            <div class="t">{{ c.e.title }}</div>
            <div class="who">{{ yrRange(c.e.year_start, c.e.year_end) }}</div>
          </div>
          <div class="stem" :style="{ height: c.h + 'px' }"></div>
          <div class="nd"></div>
        </template>
        <template v-else>
          <div class="nd"></div>
          <div class="stem" :style="{ height: c.h + 'px' }"></div>
          <div class="bx">
            <div class="t">{{ c.e.title }}</div>
            <div class="who">{{ yrRange(c.e.year_start, c.e.year_end) }}</div>
          </div>
        </template>
      </div>
      <div
        v-for="c in undatedCards"
        :key="'u' + c.e.id"
        class="tl-ev"
        :class="{ sel: c.e.id === selectedEventId }"
        :style="{ left: c.x + 'px', top: c.top + 'px', '--dc': c.color }"
        @click.stop="onCard(c.e.id)"
      >
        <template v-if="c.above">
          <div class="bx">
            <div class="t">{{ c.e.title }}</div>
            <div class="who">{{ yrRange(c.e.year_start, c.e.year_end) }}</div>
          </div>
          <div class="stem" :style="{ height: c.h + 'px' }"></div>
          <div class="nd"></div>
        </template>
        <template v-else>
          <div class="nd"></div>
          <div class="stem" :style="{ height: c.h + 'px' }"></div>
          <div class="bx">
            <div class="t">{{ c.e.title }}</div>
            <div class="who">{{ yrRange(c.e.year_start, c.e.year_end) }}</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
