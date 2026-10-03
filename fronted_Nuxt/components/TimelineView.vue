<script setup lang="ts">
import type { ChronicleEvent, Person } from '~/types/chronicle'
import { dynastyColor, yrFmt, yrRange, toggleableDynastyBands, TIMELINE_BANDS } from '~/utils/dynasty'

const props = defineProps<{
  events: ChronicleEvent[]
  persons: Person[]
  selectedEventId: number | null
  selectedPersonId: number | null
  active: boolean
  dynastyFilter: string[]
  unlitDynasties: string[]
  mode: 'events' | 'people'
}>()
const emit = defineEmits<{
  (e: 'select-event', id: number): void
  (e: 'select-person', id: number): void
}>()

const { dynasties } = useDynasties()

// —— 绝对年份线性时间轴参数 ——
// 任意年份 -> 像素:x = PAD + (year - axisStart) × K_SPAN × zoom,与分块数量/顺序无关。
// 骨架/覆盖层/事件/人物/刻度全部按绝对年份统一定位;块宽随真实跨度缩放,短朝代块自然窄(绝对刻度的天然结果)。
const axisStart = TIMELINE_BANDS[0].s // 骨架最早起始年(-3000)
const K_SPAN = 0.8 // 每单位年份的基础像素(线性比例)
const NAME_W = 30 // 与 .dyn-name 字号一致(标签文字竖排时以名称为最宽)
const PAD2 = 20 // 标签文字右侧留白(判定块宽能否放下文字)
const NAME_PAD = 24 // "不详"区块标签两侧留白
const PAD = 90 // 画布左右留白(需 ≥ 卡片半宽 75,保证最左/最右事件卡不越界被裁)
const TICK_GAP = 56 // 相邻刻度最小像素间距(低于则合并)
const CARD_W = 150 // 卡片宽度
const CARD_GAP = 6 // 相邻卡片最小间隙
const AV_W = 56 // 人物头像直径
const AV_GAP = 14 // 同侧头像最小间距

// 标签文字(竖排,名称最宽)所需宽度:按名称实际长度自动计算(兼容任意自定义朝代/国家名),块宽不足时只渲染色块。
function labelMinWidth(name: string): number {
  return NAME_W * Math.max(1, name.length) + PAD2
}

// —— 多档位垂直排布:事件上下各 2 档、人物上下各 3 档 ——
// 每档用不同 stem 高度把卡片/头像抬离轴线;最近档的 stem 已留出足够距离,保证不遮住轴线。
const EV_TIERS = [48, 122] // 事件 stem 高度(上下对称)
const AV_TIERS = [50, 130, 210] // 人物 stem 高度(上下对称)
const EV_JITTER = 8 // 事件每档随机上下浮动范围(px)
const AV_JITTER = 9 // 人物每档随机上下浮动范围(px)
const YEAR_LABEL_W = 100 // 生卒标注(人名+生卒)的最小横向间距(同侧不足则隐藏标注,避免重叠)

// id -> [0,1) 稳定哈希:用于给"不详"事件分配稳定的随机虚拟坐标、以及确定性浮动(避免抖动)
function hash01(id: number): number {
  return ((id * 2654435761) >>> 0) % 10000 / 10000
}

// 确定性伪随机(按 id 散列):同一张卡片每次渲染浮动一致,避免抖动
function jitterFor(id: number, range: number): number {
  return (hash01(id) - 0.5) * 2 * range
}

// bin 展开随缩放的连续映射:zoom ≤ BIN_OPEN_AT 时该时间点仍是一个点,zoom ≥ BIN_FULL_AT 时完全展开为最小容纳宽度。
// 用 smoothstep 缓动替代线性映射:两端(刚开始展开/即将完全展开)导数为 0,
// 消除 bin 展开/收缩在起止点的速率突变,坐标轴(被 bin 推开的内容)不再"跳一下/闪屏"。
const BIN_OPEN_AT = 1
const BIN_FULL_AT = 2.5
function binOpen(z: number): number {
  const t = Math.max(0, Math.min(1, (z - BIN_OPEN_AT) / (BIN_FULL_AT - BIN_OPEN_AT)))
  return t * t * (3 - 2 * t)
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
  if (!props.dynastyFilter.length) return datedEvents.value
  return datedEvents.value.filter((e) => props.dynastyFilter.includes(dynastyColor(e.dynasty)))
})
const filteredUndated = computed(() => {
  if (!props.dynastyFilter.length) return undatedEvents.value
  return undatedEvents.value.filter((e) => props.dynastyFilter.includes(dynastyColor(e.dynasty)))
})

// —— 人物(人物模式):锚定年份 = 生年(无生年则用卒年);生卒全无的集中到"不详"区块 ——
function personAnchorYear(p: Person): number | null {
  return p.birth_year ?? p.death_year
}
const datedPeople = computed(() => props.persons.filter((p) => personAnchorYear(p) != null))
const undatedPeople = computed(() => props.persons.filter((p) => personAnchorYear(p) == null))
const filteredPeople = computed(() => {
  if (!props.dynastyFilter.length) return datedPeople.value
  return datedPeople.value.filter((p) => props.dynastyFilter.includes(dynastyColor(p.dynasty)))
})
const filteredUndatedPeople = computed(() => {
  if (!props.dynastyFilter.length) return undatedPeople.value
  return undatedPeople.value.filter((p) => props.dynastyFilter.includes(dynastyColor(p.dynasty)))
})

// 自动扩展分块:事件/人物的年份落在可点亮分块(宏观 + 细分 + 自定义带年份)之外时,按朝代聚合生成新分块(用户新增内容自动扩展时间线)
const customBands = computed(() => {
  const known = toggleableDynastyBands(dynasties.value)
  const groups = new Map<string, { min: number; max: number }>()
  const consider = (dynasty: string, y: number, end?: number | null) => {
    if (known.some((b) => y >= b.s && y <= b.e)) return
    const lo = Math.min(y, end ?? y)
    const hi = Math.max(y, end ?? y)
    const g = groups.get(dynasty)
    if (g) {
      g.min = Math.min(g.min, lo)
      g.max = Math.max(g.max, hi)
    } else {
      groups.set(dynasty, { min: lo, max: hi })
    }
  }
  if (props.mode === 'people') {
    for (const p of datedPeople.value) consider(p.dynasty, personAnchorYear(p)!, p.death_year)
  } else {
    for (const e of datedEvents.value) consider(e.dynasty, e.year_start, e.year_end)
  }
  return [...groups.entries()].map(([name, r]) => ({
    name: name || '未知',
    color: dynastyColor(name),
    s: r.min,
    e: r.max, // 自动扩展的分块始终显示,不参与点亮/熄灭
  }))
})

// —— 骨架 + 覆盖层 ——
// 骨架 = TIMELINE_BANDS(三皇五帝→清,18 段连续不重叠):时间轴的"底",同样受点亮/熄灭控制(默认全亮)。
// 覆盖层 = 细分朝代(目录带起止年、不属于骨架)+ 自定义朝代(含新增)+ 自动扩展块:点亮盖住骨架、熄灭完全隐藏露出骨架。
// 点亮细分朝代时会自动熄灭时间重叠的骨架段(见 DynastySelect.toggleLight),保证同一时间段只展示一个区域。
const skeletonBands = computed(() =>
  TIMELINE_BANDS.map((b) => ({ ...b, lit: !props.unlitDynasties.includes(b.name), isSkeleton: true })),
)
const overlayBands = computed(() => {
  const skeletonNames = new Set(TIMELINE_BANDS.map((b) => b.name))
  const toggle = toggleableDynastyBands(dynasties.value)
    .filter((b) => !skeletonNames.has(b.name))
    .map((b) => ({ ...b, lit: !props.unlitDynasties.includes(b.name), isSkeleton: false }))
  const custom = customBands.value.map((b) => ({ ...b, lit: true, isSkeleton: false }))
  return [...toggle, ...custom]
})
// 渲染时骨架在下、覆盖在上(模板按 skeletonItems → overlayItems 顺序渲染,靠 DOM 顺序分层)。
const allBands = computed(() => [...skeletonBands.value, ...overlayBands.value])

// 时间轴最右年份:宏观骨架末端(清)铺底,再扩展到所有分块与事件/人物的最晚年份,供末端刻度使用。
// (轴左端固定从 axisStart 起,最早年份无需追踪。)
const timeDomain = computed(() => {
  let hi = TIMELINE_BANDS[TIMELINE_BANDS.length - 1].e
  const extend = (e: number) => {
    if (e > hi) hi = e
  }
  for (const b of allBands.value) extend(b.e)
  if (props.mode === 'people') {
    for (const p of datedPeople.value) extend(p.death_year ?? p.birth_year)
  } else {
    for (const e of datedEvents.value) extend(e.year_end ?? e.year_start)
  }
  return hi
})

// 每单位年份的像素(全局统一,随 zoom 缩放)
function pxPerYear(): number {
  return K_SPAN * zoom.value
}

// 年份 -> 自然像素(未计入 bin 位移):纯线性,由绝对年份唯一确定,与分块数量/顺序无关。
function xIn(y: number): number {
  return PAD + (y - axisStart) * pxPerYear()
}

// 布局:每个分块(骨架 + 覆盖层)的 x 按绝对年份线性映射,并叠加其前所有 bin 的展开位移(bin 展开会把其后内容整体右移),
// 与事件/刻度统一用 xOf 定位,保证缩放后仍对齐;块宽 = 起止年的位移差(真实跨度 + 内部 bin 展开量,最小 1px 防完全消失)。
// 短朝代块自然窄、不拉宽;文字放不下时由 labelFits 自动隐藏(只留色块)。
function computeLayout() {
  const items = allBands.value.map((b) => {
    const x0 = xOf(b.s)
    const x1 = xOf(b.e)
    const spanW = Math.max(1, x1 - x0)
    return { ...b, x0, x1, w: spanW, count: 0 }
  })
  // 按年份区间计数(骨架 + 覆盖层一致)
  for (const seg of items) {
    seg.count =
      props.mode === 'people'
        ? datedPeople.value.filter((p) => personAnchorYear(p)! >= seg.s && personAnchorYear(p)! <= seg.e).length
        : datedEvents.value.filter((e) => e.year_start >= seg.s && e.year_start <= seg.e).length
  }
  return { items }
}

const layout = computed(() => computeLayout())

// —— 事件/人物聚簇(bin):相邻节点**自然像素间距**小于一个位宽时聚为一组 ——
// 同年(同锚定年)必然聚在一起,年份接近也会聚入同一组;一组即一段"被切出"的展示长度,节点沿该段横向铺开。
// 放大到 BIN_FULL_AT 时完全展开,组内节点互不遮挡 —— 这才是"放大到最大时所有节点都能显示"的真正来源。
// 事件位宽 = 卡片宽,人物位宽 = 头像径(人物锚定年 = 生年 ?? 卒年)。
interface Cluster {
  year: number
  end: number
  evs: DatedEvent[]
  ps: Person[]
  n: number
  minW: number
  w: number
}
const clusterUnit = computed(() => (props.mode === 'people' ? AV_W + AV_GAP : CARD_W + CARD_GAP))
const clusters = computed<Cluster[]>(() => {
  const unit = clusterUnit.value
  const out: Cluster[] = []
  if (props.mode === 'people') {
    const sorted = [...filteredPeople.value].sort((a, b) => (personAnchorYear(a)! - personAnchorYear(b)!) || a.id - b.id)
    for (let i = 0; i < sorted.length; ) {
      const year = personAnchorYear(sorted[i])!
      let j = i + 1
      while (j < sorted.length && xIn(personAnchorYear(sorted[j])!) - xIn(personAnchorYear(sorted[j - 1])!) < unit) j++
      const ps = sorted.slice(i, j)
      const n = ps.length
      const minW = n * unit
      out.push({ year, end: personAnchorYear(sorted[j - 1])!, evs: [], ps, n, minW, w: n >= 2 ? minW * binOpen(zoom.value) : 0 })
      i = j
    }
  } else {
    const sorted = [...filteredDated.value].sort((a, b) => a.year_start - b.year_start || a.id - b.id)
    for (let i = 0; i < sorted.length; ) {
      const year = sorted[i].year_start
      let j = i + 1
      while (j < sorted.length && xIn(sorted[j].year_start) - xIn(sorted[j - 1].year_start) < unit) j++
      const evs = sorted.slice(i, j)
      const n = evs.length
      const minW = n * unit
      out.push({ year, end: sorted[j - 1].year_start, evs, ps: [], n, minW, w: n >= 2 ? minW * binOpen(zoom.value) : 0 })
      i = j
    }
  }
  return out
})

// 实际产生位移的聚簇:组内 ≥2 个节点才展开(单个节点无需展开、不产生位移)。
const bins = computed(() => clusters.value.filter((c) => c.n >= 2))

// 某年份之前所有已结束聚簇的宽度之和(后续分块、刻度、事件整体右移)。聚簇跨年份,按结束年判断是否"在其之前"。
function shiftBefore(y: number): number {
  let s = 0
  for (const b of bins.value) if (b.end < y) s += b.w
  return s
}

// 年份 -> 真实像素:线性自然位置 + bin 位移,所有块/事件/人物统一按此映射。
function xOf(y: number): number {
  return xIn(y) + shiftBefore(y)
}

// 仅渲染点亮的分块:熄灭的分块(骨架段或覆盖块)完全隐藏。
// 分两层渲染:骨架在下、覆盖在上(模板按 skeletonItems → overlayItems 顺序渲染,靠 DOM 顺序分层)。
const litItems = computed(() => layout.value.items.filter((b) => b.lit))
const skeletonItems = computed(() => litItems.value.filter((b) => b.isSkeleton))
const overlayItems = computed(() => litItems.value.filter((b) => !b.isSkeleton))

// 骨架标签让位:骨架块若与**点亮的**覆盖块时间重叠,则骨架**不渲染标签**(仅保留底色),
// 让覆盖块的朝代名/年份占据该时间段,消除同时间段两条文字重影。
const skeletonLabelHidden = computed(() => {
  const hidden = new Set<string>()
  for (const sk of skeletonItems.value) {
    const covered = overlayItems.value.some(
      (ov) => ov.lit && ov.s < sk.e && sk.s < ov.e,
    )
    if (covered) hidden.add(sk.name + sk.s)
  }
  return hidden
})

// 块宽是否足以放下标签文字(竖排,名称最宽):不足则只渲染色块、不写文字,缩小时文字自动消失。
function labelFits(d: { name: string; w: number }): boolean {
  return d.w >= labelMinWidth(d.name)
}

// bin 段的渲染位置(仅展开到一定宽度才标注,避免缩成点时出现碎片标签)
const binSegs = computed(() =>
  bins.value
    .map((b) => {
      const x0 = xOf(b.year)
      return { ...b, x0, x1: x0 + b.w }
    })
    .filter((b) => b.w > 24),
)

// 时间轴右端:已点亮分块(骨架 + 覆盖层)的右缘最大值(自适应,随分块拉宽/覆盖点亮而伸长)。
// 熄灭的分块不占位、不撑宽,故只取 litItems,避免熄灭后右侧残留空白,也让"缩到全览"的估算与实际一致。
const axisEnd = computed(() => {
  const ends = litItems.value.map((b) => b.x1)
  return ends.length ? Math.max(...ends) + PAD : PAD
})

// —— 无年份(事件/人物):"不详"区块固定在时间轴最右端 ——
const undatedBand = computed(() => {
  const count = props.mode === 'people' ? filteredUndatedPeople.value.length : filteredUndated.value.length
  if (!count) return { x0: 0, x1: 0, w: 0, count }
  const x0 = axisEnd.value + 40
  const unit = props.mode === 'people' ? AV_W + AV_GAP : CARD_W + CARD_GAP
  // "不详"区块随缩放一起缩,最小 = 能放下"不详"标签文字的宽度(全览时不再按卡片数量撑大)
  const w = Math.max(NAME_W * 2 + NAME_PAD, count * unit * zoom.value)
  return { x0, x1: x0 + w, w, count }
})
const totalW = computed(() => Math.max(axisEnd.value + PAD, undatedBand.value.x1 + PAD))

const undatedCards = computed(() => {
  const band = undatedBand.value
  if (!band.count || props.mode !== 'events') return []
  // 虚拟时间轴:按 id 哈希稳定随机排序,事件在虚拟轴上均匀分布;间距 = 卡片位 × zoom,随放大缩小同步拉伸/聚拢
  const ordered = [...filteredUndated.value].sort((a, b) => hash01(a.id) - hash01(b.id))
  const unit = CARD_W + CARD_GAP
  const placed = ordered.map((e, i) => ({
    e,
    color: dynastyColor(e.dynasty),
    x: band.x0 + PAD / 2 + i * unit * zoom.value,
    above: i % 2 === 0,
    stem: EV_TIERS[0] + jitterFor(e.id, EV_JITTER),
    shown: true,
  }))
  // 与有年份事件一致:一条竖线只显示一个,横向间距 < unit 时隐藏后者(隐藏项保留在 DOM 中淡入淡出),
  // 选中事件强制保留;放大拉开间距后逐个显现。
  let lastX = -Infinity
  for (const c of placed) {
    const isSel = c.e.id === props.selectedEventId
    c.shown = isSel || c.x - lastX >= unit
    if (c.shown) lastX = c.x
  }
  return placed
})

const undatedPersonCards = computed(() => {
  const band = undatedBand.value
  if (!band.count || props.mode !== 'people') return []
  // 与事件一致:虚拟时间轴随机均匀分布,间距随 zoom 缩放
  const ordered = [...filteredUndatedPeople.value].sort((a, b) => hash01(a.id) - hash01(b.id))
  const unit = AV_W + AV_GAP
  const placed = ordered.map((p, i) => ({
    p,
    color: p.color || dynastyColor(p.dynasty),
    x: band.x0 + PAD / 2 + i * unit * zoom.value,
    above: i % 2 === 0,
    stem: AV_TIERS[0] + jitterFor(p.id, AV_JITTER),
    showYr: false,
    shown: true,
  }))
  // 与有年份人物一致:一条竖线只显示一个,横向间距 < unit 时隐藏后者,选中人物强制保留;放大拉开间距后逐个显现。
  let lastX = -Infinity
  for (const c of placed) {
    const isSel = c.p.id === props.selectedPersonId
    c.shown = isSel || c.x - lastX >= unit
    if (c.shown) lastX = c.x
  }
  return placed
})

// 视口内可见的分块数:放大到只剩一个朝代块时,关闭悬浮发光
const singleBand = computed(() => {
  const x0 = scrollLeft.value
  const x1 = scrollLeft.value + (viewW.value || 1)
  return litItems.value.filter((d) => d.x1 > x0 && d.x0 < x1).length <= 1
})

// 非均匀刻度:每个朝代的起始年 + 时间线末端 + 事件年份,按像素间距去重
const ticks = computed(() => {
  const years = new Set<number>()
  for (const seg of allBands.value) years.add(seg.s)
  years.add(timeDomain.value)
  if (props.mode === 'people') for (const p of filteredPeople.value) years.add(personAnchorYear(p)!)
  // 事件模式:事件年份改由节点处 tl-ev-yr 标注,不再作为刻度显示,避免与节点标签(同 x 同字)重叠。
  // 事件模式:刻度还要避开事件节点自身的 x(节点处已显示年份),否则分块起点(如 -3000)恰有事件时两者同 x 叠字。
  const eventXs = props.mode === 'events' ? filteredDated.value.map((e) => xOf(e.year_start)) : []
  const sorted = [...years].sort((a, b) => a - b)
  const out: number[] = []
  for (const y of sorted) {
    if (out.length && Math.abs(xOf(y) - xOf(out[out.length - 1])) < TICK_GAP) continue
    if (eventXs.length && eventXs.some((ex) => Math.abs(ex - xOf(y)) < TICK_GAP)) continue
    out.push(y)
  }
  return out
})

// —— 事件卡片 ——
// 定位规则:
//   1. 每个事件落在轴线上其所属聚簇的起点 xOf(cluster.year) 处;
//   2. 聚簇内事件沿聚簇展开段均匀分布(放大到 BIN_FULL_AT 时完全展开,圆点各自铺开);
//   3. 每档(上/下各 2 档)按顺序高低错开,额外带确定性随机上下浮动,增加错落感;
//   4. 重叠隐藏:一条竖线(x)上只显示一个,横向间距不足时靠后者隐藏,放大后逐步显现。
const cards = computed(() => {
  const laneCount = EV_TIERS.length * 2
  const placed: { e: ChronicleEvent; color: string; x: number; above: boolean; lane: number; stem: number; shown: boolean }[] = []
  for (const cl of clusters.value) {
    const x0 = xOf(cl.year)
    cl.evs.forEach((e, k) => {
      let x = x0
      if (cl.w > 0 && cl.n > 1) x = x0 + (k / (cl.n - 1)) * cl.w
      const lane = k % laneCount
      const above = lane % 2 === 0
      const tier = Math.floor(lane / 2)
      const stem = EV_TIERS[tier] + jitterFor(e.id, EV_JITTER)
      placed.push({ e, color: dynastyColor(e.dynasty), x, above, lane, stem, shown: true })
    })
  }
  // 重叠隐藏:一条竖线(x)上只显示一个 —— 按横向位置去重,间距 < CARD_W+CARD_GAP 时标记 shown=false;
  // 选中事件强制保留(确保搜索高亮一定可见)。隐藏项保留在 DOM 中,靠 opacity 过渡做淡入淡出,不再突然闪现/消失。
  placed.sort((a, b) => a.x - b.x)
  let lastX = -Infinity
  for (const c of placed) {
    const isSel = c.e.id === props.selectedEventId
    c.shown = isSel || c.x - lastX >= CARD_W + CARD_GAP
    if (c.shown) lastX = c.x
  }
  return placed
})

// 有年份 + 无年份卡片合并渲染(同一套"节点锚定轴线"的结构)
const allCards = computed(() => [
  ...cards.value.map((c) => ({ ...c, key: 'd' + c.e.id })),
  ...undatedCards.value.map((c) => ({ ...c, key: 'u' + c.e.id })),
])

// —— 人物头像(人物模式):按锚定年(生年 ?? 卒年)落在轴线上,同聚簇(bin)沿展开段横向铺开,上/下各 3 档高低错开 ——
// 一条竖线(x)上只显示一个,横向间距不足时靠后者隐藏,选中人物强制保留;生卒标注只在横向空间足够时显示,避免重叠。
const personCards = computed(() => {
  const laneCount = AV_TIERS.length * 2
  const placed: { p: Person; color: string; x: number; above: boolean; lane: number; stem: number; shown: boolean; showYr: boolean }[] = []
  for (const cl of clusters.value) {
    const x0 = xOf(cl.year)
    cl.ps.forEach((p, k) => {
      let x = x0
      if (cl.w > 0 && cl.n > 1) x = x0 + (k / (cl.n - 1)) * cl.w
      const lane = k % laneCount
      const above = lane % 2 === 0
      const tier = Math.floor(lane / 2)
      const stem = AV_TIERS[tier] + jitterFor(p.id, AV_JITTER)
      placed.push({ p, color: p.color || dynastyColor(p.dynasty), x, above, lane, stem, shown: true, showYr: true })
    })
  }
  // 重叠隐藏:一条竖线(x)上只显示一个 —— 按横向位置去重,间距 < AV_W+AV_GAP 时标记 shown=false;
  // 选中人物强制保留。放大时 bin 展开增大横向距离,被隐藏的人物逐个显现(隐藏项保留在 DOM 中做淡入淡出)。
  placed.sort((a, b) => a.x - b.x)
  let lastX = -Infinity
  for (const c of placed) {
    const isSel = c.p.id === props.selectedPersonId
    c.shown = isSel || c.x - lastX >= AV_W + AV_GAP
    if (c.shown) lastX = c.x
  }
  // 生卒标注去重叠:仅在「显示中」的人物间判断,同侧相邻标注间距不足 YEAR_LABEL_W 时隐藏后者
  for (const side of [true, false]) {
    const sideCards = placed.filter((c) => c.shown && c.above === side).sort((a, b) => a.x - b.x)
    let prevX = -Infinity
    for (const c of sideCards) {
      if (c.x - prevX < YEAR_LABEL_W) c.showYr = false
      else prevX = c.x
    }
  }
  return placed
})

function personTags(p: Person): string[] {
  return (p.identity || '').split('、').filter(Boolean)
}

// 人物头像合并(有生年 + 无生年),人物模式渲染
const allPersonCards = computed(() => [
  ...personCards.value.map((c) => ({ ...c, key: 'p' + c.p.id })),
  ...undatedPersonCards.value.map((c) => ({ ...c, key: 'u' + c.p.id })),
])

// 放大上限:取能满足两个条件的最小值 ——
// 条件 1:聚簇(bin)完全展开,同一组时间接近的事件都能横向铺开显示(不被重叠隐藏);
// 条件 2:时间跨度最小的块,放大到其宽度能放下自己的名称文字(文字宽按名称长度自动计算,兼容自定义朝代/国家)。
const zoomMax = computed(() => {
  const needEvents = BIN_FULL_AT
  let minSpan = Infinity
  let minSpanName = ''
  for (const b of allBands.value) {
    const span = b.e - b.s
    if (span > 0 && span < minSpan) {
      minSpan = span
      minSpanName = b.name
    }
  }
  const needLabel = Number.isFinite(minSpan) ? labelMinWidth(minSpanName) / (minSpan * K_SPAN) : 0
  return Math.max(needEvents, needLabel)
})

// 最小缩放:让整条骨架"恰好塞进视口"(全览)。绝对刻度下骨架总宽 = zoom × K_SPAN × Σ跨度 + 2×PAD,直接解出,无需二分/写死像素。
const zoomMin = computed(() => {
  const vw = viewW.value
  if (!vw || vw < 100) return 0
  const span = TIMELINE_BANDS.reduce((a, b) => a + (b.e - b.s), 0)
  const undatedCount = props.mode === 'people' ? filteredUndatedPeople.value.length : filteredUndated.value.length
  const undatedW = undatedCount ? 40 + NAME_W * 2 + NAME_PAD : 0
  const z = (vw - 2 * PAD - undatedW) / (span * K_SPAN)
  return Math.min(zoomMax.value, Math.max(0, z))
})

// —— 拖拽横向滚动 ——
let down = false
let sx = 0
let sl = 0
let dragMoved = 0

function onDown(e: MouseEvent) {
  stopZoom() // 拖拽时停止缩放循环,避免与手动横向滚动竞争
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

function onPerson(id: number) {
  if (dragMoved > 6) return
  emit('select-person', id)
}

// —— 缩放:滚轮/按钮/拉条统一以视口中心为锚点 ——
// 锚定「年份」而非「像素」:缩放前后视口中心对应的年份保持不变。这样 bin 展开/收缩(shiftBefore 随 zoom 变化)
// 带来的位移也一并被修正,任何方式缩放都不会左右漂移。
function yearAtX(x: number): number {
  const lo = axisStart
  const hi = timeDomain.value
  if (x <= xOf(lo)) return lo
  if (x >= xOf(hi)) return hi
  let a = lo
  let b = hi
  for (let i = 0; i < 60; i++) {
    const mid = (a + b) / 2
    if (xOf(mid) < x) a = mid
    else b = mid
  }
  return (a + b) / 2
}
// —— 平滑缩放:单一 rAF 循环,zoom 按指数缓动逼近目标,每帧用 scrollAt() 重算滚动位置 ——
// 滚动锚点随 zoom 逐帧校正(如缩放时保持中心年份不动),因此 bin 展开/收缩带来的坐标轴位移被平滑过渡,不再"跳一下"。
// 与"每个事件重启一段动画"不同:高频滚轮(触控板惯性/各浏览器)只更新目标值、由同一循环持续跟随,
// 不会因反复重启缓动而方向错乱或缩放抖动;并归一化 deltaMode,消除各浏览器滚轮灵敏度差异。
let focusedS: number | null = null
let zoomTarget = 1
let scrollAt: (() => number) | null = null
let zoomTau = 90
let zoomRaf = 0

function clampZoom(z: number): number {
  return Math.min(zoomMax.value, Math.max(zoomMin.value, z))
}

// 启动/复用缩放循环:目标值与锚点每次调用都可更新,循环持续逼近最新目标(帧率无关)。
function animateTo(target: number, fn: () => number, tau = 90) {
  zoomTarget = clampZoom(target)
  scrollAt = fn
  zoomTau = tau
  if (zoomRaf) return
  let last = performance.now()
  const step = (now: number) => {
    const dt = Math.min(64, now - last)
    last = now
    const diff = zoomTarget - zoom.value
    if (Math.abs(diff) < 0.0005) {
      zoom.value = zoomTarget
      wrapEl.value!.scrollLeft = scrollAt!()
      zoomRaf = 0
      return
    }
    zoom.value += diff * (1 - Math.exp(-dt / zoomTau))
    wrapEl.value!.scrollLeft = scrollAt!()
    zoomRaf = requestAnimationFrame(step)
  }
  zoomRaf = requestAnimationFrame(step)
}

function stopZoom() {
  if (zoomRaf) {
    cancelAnimationFrame(zoomRaf)
    zoomRaf = 0
  }
}

function applyZoom(newZoom: number, tau = 90) {
  const wrap = wrapEl.value!
  const cx = wrap.clientWidth / 2
  const centerYear = yearAtX(wrap.scrollLeft + cx) // 用当前 zoom 反解中心年份
  animateTo(newZoom, () => xOf(centerYear) - cx, tau)
}

// 归一化滚轮量:不同浏览器/设备的 deltaMode 不同(0=像素/1=行/2=页),统一换算成像素量,
// 避免 Firefox/Safari(行模式 deltaY≈3)几乎缩不动、而 Chrome(像素模式 deltaY≈100)正常的差异。
function wheelDeltaY(e: WheelEvent): number {
  if (e.deltaMode === 1) return e.deltaY * 33
  if (e.deltaMode === 2) return e.deltaY * (wrapEl.value?.clientHeight || 600)
  return e.deltaY
}

function wheelDeltaX(e: WheelEvent): number {
  if (e.deltaMode === 1) return e.deltaX * 33
  if (e.deltaMode === 2) return e.deltaX * (wrapEl.value?.clientWidth || 900)
  return e.deltaX
}

function onWheel(e: WheelEvent) {
  e.preventDefault()
  const wrap = wrapEl.value!
  // 触控板横向滑动(deltaX 为主)→ 左右平移;纵向滚动(deltaY 为主)→ 缩放。
  const dx = wheelDeltaX(e)
  const dy = wheelDeltaY(e)
  if (Math.abs(dx) > Math.abs(dy)) {
    stopZoom() // 平移前停掉进行中的缩放循环,避免逐帧重设 scrollLeft 覆盖手动平移
    wrap.scrollLeft += dx
  } else {
    const cx = wrap.clientWidth / 2
    const centerYear = yearAtX(wrap.scrollLeft + cx)
    animateTo(zoom.value * Math.exp(-dy * 0.0015), () => xOf(centerYear) - cx, 80)
  }
}

// —— 右下角缩放控件(实体按钮 + 拉条) ——
function zoomStep(dir: number) {
  applyZoom(zoom.value * Math.exp(dir * 0.4), 160)
}
function onZoomInput(e: Event) {
  applyZoom(Number((e.target as HTMLInputElement).value), 60)
}
const zoomStepSize = computed(() => Math.max(0.001, (zoomMax.value - zoomMin.value) / 500))

function focusBand(seg: { s: number; e: number; w: number; x0: number; x1: number }) {
  if (dragMoved > 6) return
  const vw = wrapEl.value!.clientWidth
  if (focusedS === seg.s) {
    // 再次点击:恢复全局视图(居中整条时间线),不裁剪任何区域
    focusedS = null
    animateTo(1, () => (totalW.value - vw) / 2, 420)
  } else {
    focusedS = seg.s
    const span = Math.max(1, seg.e - seg.s) * K_SPAN
    const targetZoom = clampZoom(vw / span)
    // 用分块起止年的实时像素(X 随当前 zoom 逐帧重算)作为滚动目标,保证聚焦跟随缩放、不漂移到左端
    animateTo(targetZoom, () => (xOf(seg.s) + xOf(seg.e)) / 2 - vw / 2, 420)
  }
}

// 搜索框选中事件:平滑放大到事件可见并滚动居中到该事件(高亮由 selectedEventId 驱动)。
// 若事件落在拥挤聚簇(bin),放大到完全展开的缩放级别,确保能看到该聚簇内全部事件。
function focusEvent(id: number) {
  if (!props.active || !wrapEl.value) return
  const e = props.events.find((x) => x.id === id)
  if (!e) return
  const vw = wrapEl.value.clientWidth
  let targetZoom = clampZoom(Math.max(zoom.value, 1))
  if (e.year_start != null) {
    const bin = bins.value.find((b) => b.year <= e.year_start && e.year_start <= b.end)
    if (bin) targetZoom = clampZoom(Math.max(zoom.value, BIN_FULL_AT))
  }
  if (e.year_start == null) {
    animateTo(targetZoom, () => undatedBand.value.x0 - vw / 3, 420)
  } else {
    animateTo(targetZoom, () => xOf(e.year_start) - vw / 2, 420)
  }
}

defineExpose({ focusEvent })

function onResize() {
  if (!props.active) return
  syncScroll()
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  syncScroll() // 初始化即同步视口宽度/滚动位置,保证 zoomMin 等依赖 viewW 的计算立即生效
  wrapEl.value!.addEventListener('mousedown', onDown)
  wrapEl.value!.addEventListener('wheel', onWheel, { passive: false })
  wrapEl.value!.addEventListener('scroll', syncScroll)
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
  window.addEventListener('resize', onResize)
  // 视口宽度自适应:容器尺寸变化(窗口调整、侧栏开合等)实时同步 viewW,驱动 zoomMin 重算
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(syncScroll)
    resizeObserver.observe(wrapEl.value!)
  }
})

// 进入时的中线流光:单次扫过(非无限循环),每次点时间线按钮进入都重放一次。
const flowOn = ref(false)
let flowTimer: ReturnType<typeof setTimeout> | null = null
function playFlow() {
  flowOn.value = false
  if (flowTimer) clearTimeout(flowTimer)
  nextTick(() => {
    flowOn.value = true
    flowTimer = setTimeout(() => { flowOn.value = false }, 1750)
  })
}

// 每次进入时间线时固定的起步放大倍数:先跳到此放大态,再平滑收缩到概览。
// 与首次进入的默认 zoom(1)一致,保证无论上次离开时处于何种缩放/位置,进入都有一段可见的收缩动画。
const ENTRY_ZOOM = 1

// 切回时间线时:重测视口尺寸,并同步播放"收缩到概览"(从固定放大倍数缩回全览并居中)+ 中线流光。
watch(
  () => props.active,
  async (on) => {
    if (!on) {
      // 离开时间线:熄灭流光并清掉定时器,并停掉仍在进行的缩放循环,
      // 否则循环会在隐藏状态下继续跑,下次进入时 animateTo 因 zoomRaf 非零而提前返回、不再收缩。
      flowOn.value = false
      if (flowTimer) { clearTimeout(flowTimer); flowTimer = null }
      stopZoom()
      return
    }
    await nextTick()
    syncScroll()
    stopZoom() // 先确保没有残留的缩放循环,再启动全新的"收缩到概览"动画
    const vw = wrapEl.value?.clientWidth || 0
    if (vw) {
      // 先固定回放大起步态并居中,再动画收缩到概览,保证每次进入都有可感知的收缩过程。
      zoom.value = ENTRY_ZOOM
      wrapEl.value!.scrollLeft = (totalW.value - vw) / 2
      animateTo(zoomMin.value, () => (totalW.value - vw) / 2, 360)
    }
    playFlow()
  },
)

onBeforeUnmount(() => {
  stopZoom()
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
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
        v-for="d in skeletonItems"
        :key="'sk' + d.name + d.s"
        class="dyn-band"
        :style="{ left: d.x0 + 'px', width: d.w + 'px', '--dc': d.color }"
        @click="focusBand(d)"
      >
        <div v-if="!skeletonLabelHidden.has(d.name + d.s) && labelFits(d)" class="dyn-lab"><span class="dyn-name">{{ d.name }}</span><span class="dyn-yrs">{{ yrFmt(d.s) }}–{{ yrFmt(d.e) }}</span><span class="dyn-cnt">当前记录 {{ d.count }} {{ mode === 'people' ? '人物' : '事件' }}</span></div>
      </div>
      <div
        v-for="d in overlayItems"
        :key="'ov' + d.name + d.s"
        class="dyn-band"
        :style="{ left: d.x0 + 'px', width: d.w + 'px', '--dc': d.color }"
        @click="focusBand(d)"
      >
        <div v-if="labelFits(d)" class="dyn-lab"><span class="dyn-name">{{ d.name }}</span><span class="dyn-yrs">{{ yrFmt(d.s) }}–{{ yrFmt(d.e) }}</span><span class="dyn-cnt">当前记录 {{ d.count }} {{ mode === 'people' ? '人物' : '事件' }}</span></div>
      </div>
      <div
        v-if="undatedBand.count"
        class="dyn-band"
        :style="{ left: undatedBand.x0 + 'px', width: undatedBand.w + 'px', '--dc': '#8e8e93' }"
      >
        <div class="dyn-lab"><span class="dyn-name">不详</span><span class="dyn-yrs">未定年</span><span class="dyn-cnt">当前记录 {{ undatedBand.count }} {{ mode === 'people' ? '人物' : '事件' }}</span></div>
      </div>
      <div class="tl-axis" :class="{ flow: flowOn }"></div>
      <div v-for="y in ticks" :key="y" class="tl-tick" :style="{ left: xOf(y) + 'px' }">
        <span>{{ yrFmt(y) }}</span>
      </div>
      <div v-for="b in binSegs" :key="'bin' + b.year" class="tl-bin" :style="{ left: b.x0 + 'px', width: b.w + 'px' }">
        <span class="tl-bin-lab">{{ yrRange(b.year, b.end) }}</span>
      </div>
      <Transition name="tl-mode" mode="out-in">
        <div v-if="mode === 'events'" key="events" class="tl-mode-layer">
          <div
            v-for="c in allCards"
            :key="c.key"
            class="tl-ev"
            :class="{ sel: c.e.id === selectedEventId, above: c.above, below: !c.above, hide: !c.shown }"
            :style="{ left: c.x + 'px', '--dc': c.color, '--stem': c.stem + 'px' }"
            @click.stop="onCard(c.e.id)"
          >
            <template v-if="c.above">
              <div class="bx">
                <div class="t">{{ c.e.title }}</div>
                <div class="who">{{ yrRange(c.e.year_start, c.e.year_end, c.e.year_approx) }}</div>
              </div>
              <div class="stem"></div>
              <div class="nd"></div>
              <span v-if="c.e.year_start != null" class="tl-ev-yr">{{ yrRange(c.e.year_start, c.e.year_end, c.e.year_approx) }}</span>
            </template>
            <template v-else>
              <span v-if="c.e.year_start != null" class="tl-ev-yr">{{ yrRange(c.e.year_start, c.e.year_end, c.e.year_approx) }}</span>
              <div class="nd"></div>
              <div class="stem"></div>
              <div class="bx">
                <div class="t">{{ c.e.title }}</div>
                <div class="who">{{ yrRange(c.e.year_start, c.e.year_end, c.e.year_approx) }}</div>
              </div>
            </template>
          </div>
        </div>
        <div v-else key="people" class="tl-mode-layer">
          <div
            v-for="c in allPersonCards"
            :key="c.key"
            class="tl-person"
            :class="{ sel: c.p.id === selectedPersonId, above: c.above, below: !c.above, hide: !c.shown }"
            :style="{ left: c.x + 'px', '--dc': c.color, '--stem': c.stem + 'px' }"
            @click.stop="onPerson(c.p.id)"
          >
            <template v-if="c.above">
              <div class="tl-person-pop">
                <div class="tl-person-pop-hd">
                  <span class="nm">{{ c.p.name }}</span>
                  <span class="yr">{{ yrRange(c.p.birth_year, c.p.death_year) }}{{ c.p.dynasty ? ' · ' + c.p.dynasty : '' }}</span>
                </div>
                <p v-if="c.p.summary" class="sm">{{ c.p.summary }}</p>
                <div v-if="personTags(c.p).length" class="tg"><span v-for="t in personTags(c.p)" :key="t">{{ t }}</span></div>
              </div>
              <button class="tl-av" :aria-label="c.p.name">
                <img v-if="c.p.avatar_url" :src="c.p.avatar_url" alt="" />
                <span v-else>{{ c.p.name[0] }}</span>
              </button>
              <div class="tl-person-stem"></div>
              <div class="nd"></div>
              <span v-if="c.showYr" class="tl-person-yr"><b>{{ c.p.name }}</b><br>{{ yrRange(c.p.birth_year, c.p.death_year) }}</span>
            </template>
            <template v-else>
              <span v-if="c.showYr" class="tl-person-yr"><b>{{ c.p.name }}</b><br>{{ yrRange(c.p.birth_year, c.p.death_year) }}</span>
              <div class="nd"></div>
              <div class="tl-person-stem"></div>
              <button class="tl-av" :aria-label="c.p.name">
                <img v-if="c.p.avatar_url" :src="c.p.avatar_url" alt="" />
                <span v-else>{{ c.p.name[0] }}</span>
              </button>
              <div class="tl-person-pop">
                <div class="tl-person-pop-hd">
                  <span class="nm">{{ c.p.name }}</span>
                  <span class="yr">{{ yrRange(c.p.birth_year, c.p.death_year) }}{{ c.p.dynasty ? ' · ' + c.p.dynasty : '' }}</span>
                </div>
                <p v-if="c.p.summary" class="sm">{{ c.p.summary }}</p>
                <div v-if="personTags(c.p).length" class="tg"><span v-for="t in personTags(c.p)" :key="t">{{ t }}</span></div>
              </div>
            </template>
          </div>
        </div>
      </Transition>
    </div>
  </div>
  <div v-if="active" class="tl-zoom">
    <button class="zl-btn" title="缩小" aria-label="缩小" @click="zoomStep(-1)">−</button>
    <input
      class="zl-range"
      type="range"
      :min="zoomMin"
      :max="zoomMax"
      :step="zoomStepSize"
      :value="zoom"
      @input="onZoomInput"
    />
    <button class="zl-btn" title="放大" aria-label="放大" @click="zoomStep(1)">+</button>
  </div>
</template>
