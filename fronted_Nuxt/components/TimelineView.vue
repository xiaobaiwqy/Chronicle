<script setup lang="ts">
import type { ChronicleEvent, Person } from '~/types/chronicle'
import { dynastyColor, yrFmt, yrRange, toggleableDynastyBands, TIMELINE_BANDS, dynastyRange } from '~/utils/dynasty'

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

// 生卒标注(人名 + 生卒)横向占宽:按实际文字估算(中文≈字号宽、数字/符号≈0.6em),数据无关、不写死像素。
// 取全量有年份人物中的最大值作为相邻标注最小间距,保证放大到最大时所有标注互不重叠。
const LABEL_CJK_W = 9.5
const LABEL_ASCII_W = 6
function labelTextW(s: string): number {
  let w = 0
  for (const ch of s) w += ch >= '一' && ch <= '鿿' ? LABEL_CJK_W : LABEL_ASCII_W
  return w
}

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

// —— 人物(人物模式):锚定年份 —— 三个点依次判断:卒年落在自己朝代/国家区间内 → 用卒年;否则生年落在区间内 → 用生年;
// 两者都跑出区间(或无区间)→ 用生卒中点。让人物尽量落在其朝代标签对应的时间段里(如秦人出生在战国、卒在秦朝 → 取卒年)。
// 仍用真实年份(生/卒/中点),朝代区间来自目录/自定义朝代(dynastyRange),数据驱动、不硬编码;生卒全无的集中到"不详"区块。
function personAnchorYear(p: Person): number | null {
  const birth = p.birth_year
  const death = p.death_year
  if (birth == null && death == null) return null
  const range = dynastyRange(p.dynasty, dynasties.value)
  if (range) {
    const inRange = (y: number | null) => y != null && y >= range.s && y <= range.e
    if (inRange(death)) return death
    if (inRange(birth)) return birth
  }
  if (birth != null && death != null) return Math.round((birth + death) / 2)
  return birth ?? death
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

// 人物标注(人名 + 生卒)所需的最小横向间距:取全量有年份人物中标注最宽者,再加留白。
// 作为人物聚簇的位宽下限,放大到最大时同侧相邻头像至少拉开这么远,标注文字不重叠。
const yearLabelW = computed(() => {
  let m = 0
  for (const p of datedPeople.value) {
    m = Math.max(m, (p.name || '').length * LABEL_CJK_W, labelTextW(yrRange(p.birth_year, p.death_year)))
  }
  return Math.max(AV_W + AV_GAP, Math.ceil(m + 10))
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

// —— 同年聚簇(bin):严格按「完全同一年」分组(事件 year_start / 人物锚定年 = 生年??卒年) ——
// 同一时间点内,节点数不超过档位容量(事件 4 / 人物 6)时全靠档位上下错开,不横向展开;
// 超出容量时按「列优先」横向展开成多列(每列塞满档位),列间距一个位宽 —— 这才是 bin。
// 分组只依赖年份本身、与缩放无关,收缩时每个节点塌回自己的真实年份,不再"跳到第一个时间节点"。
interface Cluster {
  year: number
  evs: DatedEvent[]
  ps: Person[]
  n: number
  cols: number // 需要的列数(1 = 不展开)
  w: number // bin 展开宽度(列数-1 个位宽,随缩放平滑展开)
}
const clusterUnit = computed(() => (props.mode === 'people' ? yearLabelW.value : CARD_W + CARD_GAP))
const clusters = computed<Cluster[]>(() => {
  const unit = clusterUnit.value
  const capacity = props.mode === 'people' ? AV_TIERS.length * 2 : EV_TIERS.length * 2
  const open = binOpen(zoom.value)
  const out: Cluster[] = []
  if (props.mode === 'people') {
    const sorted = [...filteredPeople.value].sort((a, b) => (personAnchorYear(a)! - personAnchorYear(b)!) || a.id - b.id)
    for (let i = 0; i < sorted.length; ) {
      const year = personAnchorYear(sorted[i])!
      let j = i + 1
      while (j < sorted.length && personAnchorYear(sorted[j])! === year) j++
      const ps = sorted.slice(i, j)
      const cols = Math.ceil(ps.length / capacity)
      out.push({ year, evs: [], ps, n: ps.length, cols, w: (cols - 1) * unit * open })
      i = j
    }
  } else {
    const sorted = [...filteredDated.value].sort((a, b) => a.year_start - b.year_start || a.id - b.id)
    for (let i = 0; i < sorted.length; ) {
      const year = sorted[i].year_start
      let j = i + 1
      while (j < sorted.length && sorted[j].year_start === year) j++
      const evs = sorted.slice(i, j)
      const cols = Math.ceil(evs.length / capacity)
      out.push({ year, evs, ps: [], n: evs.length, cols, w: (cols - 1) * unit * open })
      i = j
    }
  }
  return out
})

// 实际产生横向位移的聚簇:只有超过档位容量(列数 > 1)的年份才展开、才把其后内容整体右移。
const bins = computed(() => clusters.value.filter((c) => c.cols > 1))

// 某年份之前的 bin 展开位移:纯阶梯 —— bin 展开把其后所有年份整体右移一个 bin 宽。
// (同一时间点内不按年份线性摊开,因为 bin 只会出现在单一年份,没有"内部年份跨度"可言。)
function deltaShift(y: number): number {
  let s = 0
  for (const b of bins.value) if (y > b.year) s += b.w
  return s
}

// 年份 -> 真实像素:线性自然位置 + 聚簇净展开位移,所有块/事件/人物统一按此映射。
function xOf(y: number): number {
  return xIn(y) + deltaShift(y)
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
    z: EV_TIERS.length,
  }))
  // 与有年份事件一致:上下两侧各自独立去重,同侧横向间距 < unit 时隐藏后者(隐藏项保留在 DOM 中淡入淡出),
  // 选中事件强制保留;放大拉开间距后逐个显现。
  for (const side of [true, false]) {
    let lastX = -Infinity
    for (const c of placed.filter((c) => c.above === side)) {
      const isSel = c.e.id === props.selectedEventId
      c.shown = isSel || c.x - lastX >= unit
      if (c.shown) lastX = c.x
    }
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
    z: AV_TIERS.length,
  }))
  // 与有年份人物一致:上下两侧各自独立去重,同侧横向间距 < unit 时隐藏后者,选中人物强制保留;放大拉开间距后逐个显现。
  for (const side of [true, false]) {
    let lastX = -Infinity
    for (const c of placed.filter((c) => c.above === side)) {
      const isSel = c.p.id === props.selectedPersonId
      c.shown = isSel || c.x - lastX >= unit
      if (c.shown) lastX = c.x
    }
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
//   1. 全部落在真实年份 xOf(year);同一年内不超过档位容量(4)时靠上下档位错开,不横向展开;
//   2. 同年超出容量时按「列优先」横向展开(第几列 = 序号÷容量),列间距一个位宽,随缩放平滑展开;
//   3. 档位贪心分配:所有卡片按 x 排序后从左到右,每张先占第一个能横向放下的档位(横向间距 ≥ 位宽);
//      收缩时相邻卡片先挤到不同档位,所有档位都放不下才隐藏 —— 充分利用上下档位,而非直接消失。
const cards = computed(() => {
  const laneCount = EV_TIERS.length * 2
  const unit = CARD_W + CARD_GAP
  const open = binOpen(zoom.value)
  // 展平:每个事件一个候选(先只定 x,档位随后全局贪心分配)
  const items: { e: ChronicleEvent; color: string; x: number }[] = []
  for (const cl of clusters.value) {
    cl.evs.forEach((e, k) => {
      const col = Math.floor(k / laneCount)
      items.push({ e, color: dynastyColor(e.dynasty), x: xOf(cl.year) + col * unit * open })
    })
  }
  items.sort((a, b) => a.x - b.x || a.e.id - b.e.id)
  // 全局贪心分配档位:每个档位记住最后占用的 x,横向间距 ≥ 位宽才算放下。
  const lastX = new Array<number>(laneCount).fill(-Infinity)
  const placed: { e: ChronicleEvent; color: string; x: number; above: boolean; stem: number; shown: boolean; z: number }[] = items.map((it) => {
    const isSel = it.e.id === props.selectedEventId
    let lane = -1
    for (let l = 0; l < laneCount; l++) {
      if (it.x - lastX[l] >= unit) { lane = l; break }
    }
    if (lane < 0 && isSel) lane = 0 // 选中项:全满也强制显示(压在 lane 0)
    const shown = lane >= 0
    if (shown) lastX[lane] = it.x
    const l = Math.max(0, lane)
    const tier = Math.floor(l / 2)
    return { e: it.e, color: it.color, x: it.x, above: l % 2 === 0, stem: EV_TIERS[tier] + jitterFor(it.e.id, EV_JITTER), shown, z: laneCount / 2 - tier }
  })
  return placed
})

// 有年份 + 无年份卡片合并渲染(同一套"节点锚定轴线"的结构)
const allCards = computed(() => [
  ...cards.value.map((c) => ({ ...c, key: 'd' + c.e.id })),
  ...undatedCards.value.map((c) => ({ ...c, key: 'u' + c.e.id })),
])

// —— 人物头像(人物模式):全部落在真实锚定年(生年??卒年)上,同年不超档位容量(6)时靠上下档位错开 ——
// 同年超出容量时按「列优先」横向展开;档位同样按 x 全局贪心分配(横向间距 ≥ 实测标注宽 yearLabelW),
// 收缩时相邻人物先挤到不同档位、档位放不下才隐藏 —— 显示的每个人物都带上生卒标注且互不重叠。
const personCards = computed(() => {
  const laneCount = AV_TIERS.length * 2
  const unit = yearLabelW.value
  const open = binOpen(zoom.value)
  const items: { p: Person; color: string; x: number }[] = []
  for (const cl of clusters.value) {
    cl.ps.forEach((p, k) => {
      const col = Math.floor(k / laneCount)
      items.push({ p, color: p.color || dynastyColor(p.dynasty), x: xOf(cl.year) + col * unit * open })
    })
  }
  items.sort((a, b) => a.x - b.x || a.p.id - b.p.id)
  const lastX = new Array<number>(laneCount).fill(-Infinity)
  const placed: { p: Person; color: string; x: number; above: boolean; stem: number; shown: boolean; showYr: boolean; z: number }[] = items.map((it) => {
    const isSel = it.p.id === props.selectedPersonId
    let lane = -1
    for (let l = 0; l < laneCount; l++) {
      if (it.x - lastX[l] >= unit) { lane = l; break }
    }
    if (lane < 0 && isSel) lane = 0 // 选中人物:全满也强制显示(压在 lane 0)
    const shown = lane >= 0
    if (shown) lastX[lane] = it.x
    const l = Math.max(0, lane)
    const tier = Math.floor(l / 2)
    return { p: it.p, color: it.color, x: it.x, above: l % 2 === 0, stem: AV_TIERS[tier] + jitterFor(it.p.id, AV_JITTER), shown, showYr: shown, z: laneCount / 2 - tier }
  })
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

// 数据项(共享):最挤的「容量+1」个事件/人物所需的最小缩放 —— 前 capacity 个由档位竖着叠,只有第 capacity+1 个才需要横向空间。
// 对给定年份序列,取能装下「容量+1」个的最小年份跨度 D,返回 位宽 / (D × K_SPAN);同年(跨度 0)溢出归 bin 管,跳过。
// 预留(边角):相邻年份一方 bin 展开成多列会挤占下一年的自然位置,纯年份跨度估算会略小,这里留 binMargin 余量(暂为 0)。
function densityZoom(years: number[], unit: number, capacity: number): number {
  const ys = [...years].sort((a, b) => a - b)
  let D = Infinity
  for (let i = 0; i + capacity < ys.length; i++) {
    const span = ys[i + capacity] - ys[i]
    if (span > 0 && span < D) D = span
  }
  if (!Number.isFinite(D)) return 0
  const binMargin = 0 // 预留:同年 bin 多列 + 邻年挤压的修正项(待补)
  return unit / (D * K_SPAN) + binMargin
}

// 放大上限(拉满):取三项的最小满足值 ——
// 条件 1:同年溢出 bin 完全展开(固定阈值,与数据无关);
// 条件 2(数据项):最挤的「容量+1」个事件/人物横向分开(densityZoom,见上);
// 条件 3:所有朝代背景文字放下 —— 遍历每个块,取「文字宽 ÷ 跨度」最大者。
const zoomMax = computed(() => {
  const needBin = BIN_FULL_AT
  const unit = props.mode === 'people' ? yearLabelW.value : CARD_W + CARD_GAP
  const capacity = props.mode === 'people' ? AV_TIERS.length * 2 : EV_TIERS.length * 2
  const years = props.mode === 'people'
    ? filteredPeople.value.map((p) => personAnchorYear(p)!)
    : filteredDated.value.map((e) => e.year_start)
  const needGap = densityZoom(years, unit, capacity)
  let needLabel = 0
  for (const b of allBands.value) {
    const span = b.e - b.s
    if (span > 0) needLabel = Math.max(needLabel, labelMinWidth(b.name) / (span * K_SPAN))
  }
  return Math.max(needBin, needGap, needLabel)
})

// 单个分块的数据项缩放:把「数据项」限定到该块 [s,e] 区间内的事件/人物,计算块内全部可见所需的放大倍数。
// 与全局 zoomMax 同构:max(同年 bin 展开, 块内最挤「容量+1」跨度, 块标签放下),必然 ≤ 全局 zoomMax。
function bandDataZoom(seg: { name: string; s: number; e: number }): number {
  const unit = props.mode === 'people' ? yearLabelW.value : CARD_W + CARD_GAP
  const capacity = props.mode === 'people' ? AV_TIERS.length * 2 : EV_TIERS.length * 2
  const years = props.mode === 'people'
    ? filteredPeople.value.filter((p) => personAnchorYear(p)! >= seg.s && personAnchorYear(p)! <= seg.e).map((p) => personAnchorYear(p)!)
    : filteredDated.value.filter((e) => e.year_start >= seg.s && e.year_start <= seg.e).map((e) => e.year_start)
  const needGap = densityZoom(years, unit, capacity)
  const span = Math.max(1, seg.e - seg.s)
  const needLabel = labelMinWidth(seg.name) / (span * K_SPAN)
  return Math.max(BIN_FULL_AT, needGap, needLabel)
}

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
  stopScrollAnim()
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
// 锚定「年份」而非「像素」:缩放前后视口中心对应的年份保持不变。这样 bin 展开/收缩(deltaShift 随 zoom 变化)
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
  stopScrollAnim() // 缩放动画启动时停掉进行中的横向滚动动画,避免两套循环同时写 scrollLeft
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
    stopScrollAnim()
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

// —— 底部居中左右滑动便捷条(左右按钮 + 会"滚动"的齿轮侧面) ——
// 整条滑条就是齿轮的侧面:通体竖线 = 轮齿,四周(上下左右)渐隐到透明;
// 齿纹随位置平移(background-position-x),像齿轮表面在滚动,页面随之左右移动。
const ROLL_PX = 140 // 全程(0..1)齿纹平移的像素量(约 14 个齿距)
const TRACK_WHEEL_SPEED = 3 // 齿轮上滑动比页面滑动更快:小控件代表整条时间线,快速拖过
const scrollMax = computed(() => Math.max(0, totalW.value - viewW.value))
// 齿纹位置独立维护(px):抓取(直接操作)时齿纹跟手向右,滑动/按钮/内容滚动(间接)时齿纹与内容反向 ——
// 两种交互方向相反,不能由 scrollRatio 纯函数推导,改为状态 gearPos 累积。
const gearPos = ref(0)
let gearDragging = false
const gearTeethScale = computed(() => (scrollMax.value > 0 ? ROLL_PX / scrollMax.value : 0))
// 非抓取来源的滚动(滑动/按钮/内容拖拽/缩放等):齿纹反向平移,像内容从齿轮下穿过。
watch(scrollLeft, (nv, ov) => {
  if (gearDragging) return
  gearPos.value -= (nv - ov) * gearTeethScale.value
})
const rollerStyle = computed(() => ({
  backgroundPositionX: `${gearPos.value.toFixed(1)}px`,
}))
// —— 平滑横向滚动(左右按钮):与缩放循环同款指数缓动,帧率无关 ——
let scrollTarget = 0
let scrollTau = 160
let scrollRaf = 0

function stopScrollAnim() {
  if (scrollRaf) {
    cancelAnimationFrame(scrollRaf)
    scrollRaf = 0
  }
}

// 目标值可随时更新,由同一循环持续跟随;逼近到 0.5px 内即吸附到位并停帧。
function smoothScrollTo(target: number, tau = 160) {
  stopZoom() // 与缩放循环互斥,避免两套逐帧写 scrollLeft 竞争
  scrollTarget = Math.min(scrollMax.value, Math.max(0, target))
  scrollTau = tau
  if (scrollRaf) return
  let last = performance.now()
  const step = (now: number) => {
    const dt = Math.min(64, now - last)
    last = now
    const wrap = wrapEl.value!
    const diff = scrollTarget - wrap.scrollLeft
    if (Math.abs(diff) < 0.5) {
      wrap.scrollLeft = scrollTarget
      scrollRaf = 0
      return
    }
    wrap.scrollLeft += diff * (1 - Math.exp(-dt / scrollTau))
    scrollRaf = requestAnimationFrame(step)
  }
  scrollRaf = requestAnimationFrame(step)
}

function scrollStep(dir: number) {
  if (scrollMax.value <= 0) return
  const step = Math.max(90, viewW.value * 0.6)
  smoothScrollTo((wrapEl.value?.scrollLeft ?? 0) + dir * step)
}
function applyScrollRatio(t: number) {
  const wrap = wrapEl.value
  if (!wrap) return
  stopScrollAnim() // 齿轮拖拽直接接管位置,停掉按钮动画
  wrap.scrollLeft = Math.min(scrollMax.value, Math.max(0, t * scrollMax.value))
}
const scrollTrackEl = ref<HTMLElement | null>(null)
let lastGearX = 0
// 指针横坐标 → 0..1(整条滚轮满宽,直接线性映射)
function gearRatioAt(e: PointerEvent): number {
  const el = scrollTrackEl.value
  if (!el) return 0
  const rect = el.getBoundingClientRect()
  if (rect.width <= 0) return 0
  return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
}
function onGearDown(e: PointerEvent) {
  if (scrollMax.value <= 0) return
  e.preventDefault()
  gearDragging = true
  lastGearX = e.clientX
  stopZoom()
  ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  applyScrollRatio(gearRatioAt(e))
}
function onGearMove(e: PointerEvent) {
  if (!gearDragging) return
  const dx = e.clientX - lastGearX
  lastGearX = e.clientX
  gearPos.value += dx // 抓取:齿纹直接跟手(1:1),与滑动方向相反
  applyScrollRatio(gearRatioAt(e))
}
function onGearUp(e: PointerEvent) {
  if (!gearDragging) return
  gearDragging = false
  try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId) } catch {}
}

// 齿轮上左右滑动(触控板横滑/横向滚轮)也驱动横向滚动,不用抓取也能移动
function onTrackWheel(e: WheelEvent) {
  if (scrollMax.value <= 0) return
  stopZoom()
  stopScrollAnim()
  const dx = wheelDeltaX(e)
  const dy = wheelDeltaY(e)
  const delta = Math.abs(dx) > Math.abs(dy) ? dx : dy
  wrapEl.value!.scrollLeft = Math.min(scrollMax.value, Math.max(0, wrapEl.value!.scrollLeft + delta * TRACK_WHEEL_SPEED))
}

function focusBand(seg: { name: string; s: number; e: number; w: number; x0: number; x1: number }) {
  if (dragMoved > 6) return
  const vw = wrapEl.value!.clientWidth
  if (focusedS === seg.s) {
    // 再次点击:恢复全局视图(居中整条时间线),不裁剪任何区域
    focusedS = null
    animateTo(1, () => (totalW.value - vw) / 2, 420)
  } else {
    focusedS = seg.s
    // 点击分块:放大到「块内全部事件/人物可见」所需的放大倍数(bandDataZoom),而非铺满视口。
    const targetZoom = clampZoom(bandDataZoom(seg))
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
    const bin = bins.value.find((b) => b.year === e.year_start)
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
      stopScrollAnim()
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
  stopScrollAnim()
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
        <span class="tl-bin-lab">{{ yrFmt(b.year) }}</span>
      </div>
      <Transition name="tl-mode" mode="out-in">
        <div v-if="mode === 'events'" key="events" class="tl-mode-layer">
          <div
            v-for="c in allCards"
            :key="c.key"
            class="tl-ev"
            :class="{ sel: c.e.id === selectedEventId, above: c.above, below: !c.above, hide: !c.shown }"
            :style="{ left: c.x + 'px', '--dc': c.color, '--stem': c.stem + 'px', '--z': c.z }"
          >
            <template v-if="c.above">
              <div class="bx" @click.stop="onCard(c.e.id)">
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
              <div class="bx" @click.stop="onCard(c.e.id)">
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
            :style="{ left: c.x + 'px', '--dc': c.color, '--stem': c.stem + 'px', '--z': c.z }"
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
              <button class="tl-av" :aria-label="c.p.name" @click.stop="onPerson(c.p.id)">
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
              <button class="tl-av" :aria-label="c.p.name" @click.stop="onPerson(c.p.id)">
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
  <div v-if="active" class="tl-scroll">
    <button class="tl-scroll-btn" title="向左" aria-label="向左" @click="scrollStep(-1)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
    </button>
    <div
      class="tl-scroll-track"
      ref="scrollTrackEl"
      aria-label="横向滚动位置"
      @pointerdown="onGearDown"
      @pointermove="onGearMove"
      @pointerup="onGearUp"
      @pointercancel="onGearUp"
      @wheel.prevent="onTrackWheel"
    >
      <div class="tl-scroll-roller" :style="rollerStyle"></div>
      <div class="tl-scroll-light"></div>
    </div>
    <button class="tl-scroll-btn" title="向右" aria-label="向右" @click="scrollStep(1)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
    </button>
  </div>
</template>
