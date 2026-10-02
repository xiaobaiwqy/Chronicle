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
const CARD_W = 150 // 卡片宽度
const CARD_GAP = 6 // 相邻卡片最小间隙
const ZOOM_MIN = 0.25

// bin 展开随缩放的连续映射:zoom ≤ BIN_OPEN_AT 时该时间点仍是一个点,zoom ≥ BIN_FULL_AT 时完全展开为最小容纳宽度。
const BIN_OPEN_AT = 1
const BIN_FULL_AT = 2.5
function binOpen(z: number): number {
  return Math.max(0, Math.min(1, (z - BIN_OPEN_AT) / (BIN_FULL_AT - BIN_OPEN_AT)))
}

const wrapEl = ref<HTMLElement | null>(null)
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

// 布局:用给定 zoom 计算各分块的自然宽度与自然起始像素(分块宽度 = max(名称兜底, (年份跨度×K_SPAN + 事件数×K_EVENT) × zoom))
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

// 年份 -> 自然像素(未计入 bin 位移):分块内按年份线性,分块间按累积偏移;超出范围线性外推
function xIn(y: number, items: { s: number; e: number; w: number; x0: number; x1: number }[]): number {
  if (!items.length) return PAD
  const first = items[0]
  if (y < first.s) return first.x0 + (y - first.s) * K_SPAN
  for (const seg of items) {
    if (y >= seg.s && y <= seg.e) {
      const denom = seg.e - seg.s
      // 自定义分块可能 s===e(仅单一年份且无结束年):退化为取分块中点
      return seg.x0 + (denom === 0 ? 0.5 : (y - seg.s) / denom) * seg.w
    }
  }
  const last = items[items.length - 1]
  return last.x1 + (y - last.e) * K_SPAN
}

// —— bin 节点:同一年 ≥3 个事件时,该时间点被"切出"并插入一段展示长度 ——
const bins = computed(() => {
  const sorted = [...filteredDated.value].sort((a, b) => a.year_start - b.year_start)
  const out: { year: number; n: number; minW: number; w: number }[] = []
  for (let i = 0; i < sorted.length; ) {
    const y = sorted[i].year_start
    let j = i
    while (j < sorted.length && sorted[j].year_start === y) j++
    const n = j - i
    if (n >= 3) {
      const minW = n * (CARD_W + CARD_GAP) // 容纳该时间点全部事件的最小长度
      out.push({ year: y, n, minW, w: minW * binOpen(zoom.value) })
    }
    i = j
  }
  return out
})

// 某年份之前所有 bin 的宽度之和(后续分块、刻度、事件整体右移)
function shiftBefore(y: number): number {
  let s = 0
  for (const b of bins.value) if (b.year < y) s += b.w
  return s
}

// 年份 -> 真实像素(自然位置 + 之前 bin 的累积位移)
function X(y: number): number {
  return xIn(y, layout.value.items) + shiftBefore(y)
}

// 分块在计入 bin 位移后的实际渲染位置(后续内容整体右移)
const shiftedItems = computed(() =>
  layout.value.items.map((seg) => {
    const x0 = seg.x0 + shiftBefore(seg.s)
    const x1 = seg.x1 + shiftBefore(seg.e)
    return { ...seg, x0, x1, w: x1 - x0 }
  }),
)

// bin 段的渲染位置(仅展开到一定宽度才标注,避免缩成点时出现碎片标签)
const binSegs = computed(() =>
  bins.value
    .map((b) => {
      const x0 = xIn(b.year, layout.value.items) + shiftBefore(b.year)
      return { ...b, x0, x1: x0 + b.w }
    })
    .filter((b) => b.w > 24),
)

// —— 无年份事件:"不详"区块固定在时间轴最右端 ——
const undatedBand = computed(() => {
  const count = filteredUndated.value.length
  if (!count) return { x0: 0, x1: 0, w: 0, count }
  const items = shiftedItems.value
  const x0 = (items.length ? items[items.length - 1].x1 : PAD) + 40
  const w = Math.max(NAME_W * 2 + NAME_PAD, count * (CARD_W + CARD_GAP) + PAD)
  return { x0, x1: x0 + w, w, count }
})
const totalW = computed(() => {
  const items = shiftedItems.value
  const axisEnd = items.length ? items[items.length - 1].x1 + PAD : PAD
  return Math.max(axisEnd, undatedBand.value.x1 + PAD)
})

const undatedCards = computed(() => {
  const band = undatedBand.value
  if (!band.count) return []
  return filteredUndated.value.map((e, i) => ({
    e,
    color: dynastyColor(e.dynasty),
    x: band.x0 + PAD / 2 + i * (CARD_W + CARD_GAP),
    above: i % 2 === 0,
  }))
})

// 视口内可见的分块数:放大到只剩一个朝代块时,关闭悬浮发光
const singleBand = computed(() => {
  const x0 = scrollLeft.value
  const x1 = scrollLeft.value + (viewW.value || 1)
  return shiftedItems.value.filter((d) => d.x1 > x0 && d.x0 < x1).length <= 1
})

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

// —— 事件卡片 ——
// 定位规则:
//   1. 每个事件圆点严格落在轴线上它的真实年份 X(year) 处;
//   2. 同一时间节点 1~2 个事件:圆点重合,卡片上下错开(第 1 个在上、第 2 个在下),不横向占位;
//   3. 同一时间节点 ≥3 个事件:该点展开成一段 bin,事件沿轴在段内均匀分布(圆点仍在轴线上),卡片上下交替;
//   4. 重叠隐藏:同侧卡片横向间距不足时靠后者隐藏,放大后逐步显现。
const cards = computed(() => {
  const sorted = [...filteredDated.value].sort((a, b) => a.year_start - b.year_start || a.id - b.id)
  const nodes: { year: number; evs: ChronicleEvent[] }[] = []
  for (let i = 0; i < sorted.length; ) {
    const y = sorted[i].year_start
    let j = i
    while (j < sorted.length && sorted[j].year_start === y) j++
    nodes.push({ year: y, evs: sorted.slice(i, j) })
    i = j
  }
  const placed: { e: ChronicleEvent; color: string; x: number; above: boolean }[] = []
  for (const node of nodes) {
    const n = node.evs.length
    const bin = bins.value.find((b) => b.year === node.year)
    const x0 = xIn(node.year, layout.value.items) + shiftBefore(node.year)
    node.evs.forEach((e, k) => {
      let x = x0
      if (bin && bin.w > 0) x = x0 + (n <= 1 ? bin.w / 2 : (k / (n - 1)) * bin.w)
      placed.push({ e, color: dynastyColor(e.dynasty), x, above: k % 2 === 0 })
    })
  }
  // 重叠隐藏:上下两侧互不影响,同侧横向间距 < CARD_W+CARD_GAP 时靠后者隐藏;选中事件强制保留,确保搜索高亮一定可见
  placed.sort((a, b) => a.x - b.x)
  const keep: { e: ChronicleEvent; color: string; x: number; above: boolean }[] = []
  let lastAbove = -Infinity
  let lastBelow = -Infinity
  for (const c of placed) {
    const isSel = c.e.id === props.selectedEventId
    if (c.above) {
      if (isSel || c.x - lastAbove >= CARD_W + CARD_GAP) {
        keep.push(c)
        lastAbove = c.x
      }
    } else if (isSel || c.x - lastBelow >= CARD_W + CARD_GAP) {
      keep.push(c)
      lastBelow = c.x
    }
  }
  return keep
})

// 有年份 + 无年份卡片合并渲染(同一套"节点锚定轴线"的结构)
const allCards = computed(() => [
  ...cards.value.map((c) => ({ ...c, key: 'd' + c.e.id })),
  ...undatedCards.value.map((c) => ({ ...c, key: 'u' + c.e.id })),
])

// 事件横向铺开即可全部展示,放大上限固定。
const zoomMax = computed(() => 6)

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

function focusBand(seg: { s: number; e: number; w: number; x0: number; x1: number }) {
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
    // 用分块起止年的实时像素(X 随当前 zoom 逐帧重算)作为滚动目标,保证聚焦跟随缩放、不漂移到左端
    animateTo(targetZoom, () => (X(seg.s) + X(seg.e)) / 2 - vw / 2)
  }
}

// 搜索框选中事件:平滑放大到事件可见并滚动居中到该事件(高亮由 selectedEventId 驱动)。
// 若事件落在拥挤节点(bin),放大到完全展开的缩放级别,确保能看到该时间点全部事件。
function focusEvent(id: number) {
  if (!props.active || !wrapEl.value) return
  const e = props.events.find((x) => x.id === id)
  if (!e) return
  const vw = wrapEl.value.clientWidth
  let targetZoom = Math.min(zoomMax.value, Math.max(zoom.value, 1))
  if (e.year_start != null) {
    const bin = bins.value.find((b) => b.year === e.year_start)
    if (bin) targetZoom = Math.min(zoomMax.value, Math.max(zoom.value, BIN_FULL_AT))
  }
  if (e.year_start == null) {
    animateTo(targetZoom, () => undatedBand.value.x0 - vw / 3)
  } else {
    animateTo(targetZoom, () => X(e.year_start) - vw / 2)
  }
}

defineExpose({ focusEvent })

function onResize() {
  if (!props.active) return
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
        v-for="d in shiftedItems"
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
      <div v-for="b in binSegs" :key="'bin' + b.year" class="tl-bin" :style="{ left: b.x0 + 'px', width: b.w + 'px' }">
        <span class="tl-bin-lab">{{ yrFmt(b.year) }}</span>
      </div>
      <div
        v-for="c in allCards"
        :key="c.key"
        class="tl-ev"
        :class="{ sel: c.e.id === selectedEventId, above: c.above, below: !c.above }"
        :style="{ left: c.x + 'px', '--dc': c.color }"
        @click.stop="onCard(c.e.id)"
      >
        <template v-if="c.above">
          <div class="bx">
            <div class="t">{{ c.e.title }}</div>
            <div class="who">{{ yrRange(c.e.year_start, c.e.year_end, c.e.year_approx) }}</div>
          </div>
          <div class="stem"></div>
          <div class="nd"></div>
        </template>
        <template v-else>
          <div class="nd"></div>
          <div class="stem"></div>
          <div class="bx">
            <div class="t">{{ c.e.title }}</div>
            <div class="who">{{ yrRange(c.e.year_start, c.e.year_end, c.e.year_approx) }}</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
