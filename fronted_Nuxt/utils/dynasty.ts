// 朝代配色与年份格式化 —— 与高保真原型逐字一致(视觉主干)
// 内置朝代编年目录:用于关系网图例、添加/编辑人物的朝代下拉。

// 时间线完整分块(三皇五帝→清,连续不重叠的宏观区间):用于时间线背景色带。
// 颜色 = 该朝代的边色(dynastyColor),与关系网、事件卡片保持一致。
export interface TimelineBand {
  name: string
  color: string
  s: number
  e: number
}

export const TIMELINE_BANDS: TimelineBand[] = [
  { name: '三皇五帝', color: '#6d4c41', s: -3000, e: -2071 },
  { name: '夏', color: '#8d6e63', s: -2070, e: -1600 },
  { name: '商', color: '#c7771f', s: -1600, e: -1046 },
  { name: '西周', color: '#b0a04a', s: -1046, e: -771 },
  { name: '春秋', color: '#7d7aff', s: -770, e: -476 },
  { name: '战国', color: '#0a84ff', s: -475, e: -221 },
  { name: '秦', color: '#30d158', s: -221, e: -206 },
  { name: '汉', color: '#ff9f0a', s: -206, e: 220 },
  { name: '三国', color: '#00bcd4', s: 220, e: 265 },
  { name: '晋', color: '#9575cd', s: 265, e: 420 },
  { name: '南北朝', color: '#4db6ac', s: 420, e: 581 },
  { name: '隋', color: '#26c6da', s: 581, e: 618 },
  { name: '唐', color: '#f06292', s: 618, e: 907 },
  { name: '五代十国', color: '#bcaaa4', s: 907, e: 960 },
  { name: '宋', color: '#90a4ae', s: 960, e: 1271 },
  { name: '元', color: '#37474f', s: 1271, e: 1368 },
  { name: '明', color: '#ff7043', s: 1368, e: 1644 },
  { name: '清', color: '#5c6bc0', s: 1644, e: 1912 },
]

export interface DynastyEntry {
  name: string
  color: string
  s?: number
  e?: number
}

// 内置朝代与主要诸侯国(按历史先后顺序,三皇五帝 → 清,颜色错开不重合)。
export const DYNASTY_CATALOG: DynastyEntry[] = [
  { name: '三皇五帝', color: '#6d4c41', s: -3000, e: -2070 },
  { name: '夏', color: '#8d6e63', s: -2070, e: -1600 },
  { name: '商', color: '#c7771f', s: -1600, e: -1046 },
  { name: '西周', color: '#b0a04a', s: -1046, e: -771 },
  { name: '西周·齐', color: '#fb8c00', s: -1046, e: -771 },
  { name: '西周·鲁', color: '#00897b', s: -1046, e: -771 },
  { name: '西周·燕', color: '#7b1fa2', s: -1046, e: -771 },
  { name: '西周·晋', color: '#e53935', s: -1046, e: -771 },
  { name: '西周·宋', color: '#795548', s: -1046, e: -771 },
  { name: '东周', color: '#a1887f', s: -770, e: -256 },
  { name: '春秋', color: '#7d7aff', s: -770, e: -476 },
  { name: '春秋·齐', color: '#d81b60', s: -770, e: -476 },
  { name: '春秋·晋', color: '#1e88e5', s: -770, e: -476 },
  { name: '春秋·楚', color: '#43a047', s: -770, e: -476 },
  { name: '春秋·秦', color: '#fdd835', s: -770, e: -476 },
  { name: '春秋·宋', color: '#3949ab', s: -770, e: -476 },
  { name: '战国', color: '#0a84ff', s: -475, e: -221 },
  { name: '战国·齐', color: '#7cb342', s: -475, e: -221 },
  { name: '战国·楚', color: '#c62828', s: -475, e: -221 },
  { name: '战国·燕', color: '#ff6482', s: -475, e: -221 },
  { name: '战国·韩', color: '#26a69a', s: -475, e: -221 },
  { name: '战国·赵', color: '#d4b800', s: -475, e: -221 },
  { name: '战国·魏', color: '#8e24aa', s: -475, e: -221 },
  { name: '战国·秦', color: '#546e7a', s: -475, e: -221 },
  { name: '秦', color: '#30d158', s: -221, e: -206 },
  { name: '西汉', color: '#ff8f00', s: -202, e: 8 },
  { name: '新', color: '#ef5350', s: 9, e: 23 },
  { name: '东汉', color: '#fbc02d', s: 25, e: 220 },
  { name: '三国', color: '#00bcd4', s: 220, e: 280 },
  { name: '西晋', color: '#7e57c2', s: 266, e: 316 },
  { name: '东晋', color: '#5e35b1', s: 317, e: 420 },
  { name: '南北朝', color: '#4db6ac', s: 420, e: 589 },
  { name: '隋', color: '#26c6da', s: 581, e: 618 },
  { name: '唐', color: '#f06292', s: 618, e: 907 },
  { name: '五代十国', color: '#bcaaa4', s: 907, e: 960 },
  { name: '宋', color: '#90a4ae', s: 960, e: 1279 },
  { name: '元', color: '#37474f', s: 1271, e: 1368 },
  { name: '明', color: '#ff7043', s: 1368, e: 1644 },
  { name: '清', color: '#5c6bc0', s: 1644, e: 1912 },
]

// 遗留复合朝代(如"战国·赵")的归属类:dynastyColor 用它兜底取色(返回的类名仅作内部 token,不再作为 CSS 类)。
export function dynastyClass(d: string): string {
  if (!d) return 'dyn-default'
  if (d.includes('赵')) return 'dyn-zhao'
  if (d.includes('燕')) return 'dyn-yan'
  if (d.includes('战国')) return 'dyn-zhanguo'
  if (d.includes('秦')) return 'dyn-qin'
  if (d.includes('汉')) return 'dyn-han'
  if (d.includes('春秋')) return 'dyn-chunqiu'
  return 'dyn-default'
}

// 稳定哈希 -> 颜色:为自定义朝代分配一个稳定、可区分的主色
export function hashColor(s: string): string {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return `hsl(${h % 360}, 60%, 52%)`
}

// 独立管理的自定义朝代颜色映射:由 useDynasties 拉取后注入,dynastyColor 优先用它(用户可编辑颜色)。
const customColorMap = new Map<string, string>()

export function setCustomDynastyColors(list: { name: string; color: string }[]) {
  customColorMap.clear()
  for (const d of list) {
    if (d.name && d.color) customColorMap.set(d.name, d.color)
  }
}

// 朝代 -> 十六进制色:自定义朝代(用户指定色)优先;其次目录精确匹配;其次宏观分块(汉/晋等未入目录);再其次遗留复合映射;最后哈希。
export function dynastyColor(d: string): string {
  if (!d) return '#8e8e93'
  const custom = customColorMap.get(d)
  if (custom) return custom
  const hit = DYNASTY_CATALOG.find((x) => x.name === d)
  if (hit) return hit.color
  const band = TIMELINE_BANDS.find((b) => b.name === d)
  if (band) return band.color
  const cls = dynastyClass(d)
  if (cls === 'dyn-zhao') return '#d4b800'
  if (cls === 'dyn-yan') return '#ff6482'
  if (cls === 'dyn-zhanguo') return '#0a84ff'
  if (cls === 'dyn-qin') return '#30d158'
  if (cls === 'dyn-han') return '#ff9f0a'
  if (cls === 'dyn-chunqiu') return '#7d7aff'
  return hashColor(d)
}

// 朝代下拉选项:内置目录(按先后顺序) + 自定义朝代(后端独立管理,可带用户色) + 数据里被动出现的自定义朝代,按起始年升序。
export function dynastyOptions(
  persons: { dynasty: string }[],
  custom: { name: string; color: string }[] = [],
): { name: string; color: string }[] {
  const seen = new Set<string>()
  const out: { name: string; color: string; s: number }[] = []
  for (const d of DYNASTY_CATALOG) {
    seen.add(d.name)
    out.push({ name: d.name, color: d.color, s: d.s ?? 9999 })
  }
  for (const c of custom) {
    if (!c.name || seen.has(c.name)) continue
    seen.add(c.name)
    out.push({ name: c.name, color: c.color || hashColor(c.name), s: dynastySortYear(c.name) })
  }
  for (const p of persons) {
    const d = p.dynasty
    if (!d || seen.has(d)) continue
    seen.add(d)
    out.push({ name: d, color: dynastyColor(d), s: dynastySortYear(d) })
  }
  out.sort((a, b) => a.s - b.s)
  return out.map(({ name, color }) => ({ name, color }))
}

// 自定义朝代的起始年(用于排序):识别西周/东周/春秋/战国/秦汉等复合时期,未知的排到最后。
function dynastySortYear(name: string): number {
  if (name.includes('西周')) return -1046
  if (name.includes('东周')) return -770
  if (name.includes('春秋')) return -770
  if (name.includes('战国')) return -475
  if (name.includes('秦')) return -221
  if (name.includes('汉')) return -202
  return 9999
}

// 年份展示:负数 -> "前260"
export function yrFmt(y: number | null | undefined): string {
  if (y === null || y === undefined) return ''
  return y < 0 ? `前${-y}` : `${y}`
}

// 年份区间:两者相同时显示单个;缺一侧用 "?" 占位;都缺则 "不详";approx 时加 "约" 前缀。
export function yrRange(a: number | null, b: number | null, approx = false): string {
  if (a === null && b === null) return '不详'
  const start = a === null ? '?' : yrFmt(a)
  const end = b === null ? '?' : yrFmt(b)
  const r = start === end ? start : `${start}–${end}`
  return approx ? `约${r}` : r
}

// 解析年份输入:支持 "~" / "约" 前缀或后缀表示「约」(如 "~-260" / "-260~" / "约-260"),
// 负数或「前」前缀表示公元前(如 "-260" / "前260" 等价,与展示"前260"一致)。
export function parseYear(raw: string): { year: number | null; approx: boolean } {
  const t = (raw || '').trim()
  const approx = /[~约]/.test(t)
  const neg = t.includes('前') || t.includes('-')
  const digits = t.replace(/[^0-9]/g, '')
  if (!digits) return { year: null, approx }
  const abs = Number(digits)
  if (Number.isNaN(abs)) return { year: null, approx }
  return { year: neg ? -abs : abs, approx }
}

// —— 可点亮/熄灭的时间分块(朝代/国家 → 时间区间)—— 用于时间轴背景分块、关系网按区间显隐。

export interface TimeRange {
  s: number
  e: number
}

export interface ToggleableBand extends TimeRange {
  name: string
  color: string
}

// 某朝代/国家的起止区间:自定义朝代(带起止年)优先,其次目录细分,再其次宏观分块;无区间返回 null。
export function dynastyRange(
  name: string,
  custom: { name: string; start_year: number | null; end_year: number | null }[] = [],
): TimeRange | null {
  if (!name) return null
  const c = custom.find((d) => d.name === name && d.start_year != null)
  if (c && c.start_year != null) {
    const s = c.start_year
    return { s, e: c.end_year != null ? Math.max(s, c.end_year) : s }
  }
  const hit = DYNASTY_CATALOG.find((x) => x.name === name && x.s != null && x.e != null)
  if (hit && hit.s != null && hit.e != null) return { s: hit.s, e: hit.e }
  const band = TIMELINE_BANDS.find((b) => b.name === name)
  if (band) return { s: band.s, e: band.e }
  return null
}

// 两个时间区间是否重叠(端点相接视为不重叠)。
export function rangesOverlap(a: TimeRange, b: TimeRange): boolean {
  return a.s < b.e && b.s < a.e
}

// 可点亮/熄灭的朝代分块全集:宏观分块(18 个) + 目录里带起止年的细分朝代(战国·齐/西汉/东晋…)+ 自定义带年份朝代,按起始年升序。
export function toggleableDynastyBands(
  custom: { name: string; color: string; start_year: number | null; end_year: number | null }[] = [],
): ToggleableBand[] {
  const seen = new Set<string>()
  const out: ToggleableBand[] = []
  for (const b of TIMELINE_BANDS) {
    seen.add(b.name)
    out.push({ name: b.name, color: b.color, s: b.s, e: b.e })
  }
  for (const d of DYNASTY_CATALOG) {
    if (d.s == null || d.e == null || seen.has(d.name)) continue
    seen.add(d.name)
    out.push({ name: d.name, color: d.color, s: d.s, e: d.e })
  }
  for (const c of custom) {
    if (c.start_year == null || seen.has(c.name)) continue
    seen.add(c.name)
    const s = c.start_year
    out.push({
      name: c.name,
      color: c.color || hashColor(c.name),
      s,
      e: c.end_year != null ? Math.max(s, c.end_year) : s,
    })
  }
  return out.sort((a, b) => a.s - b.s || a.e - b.e)
}

// 默认熄灭的朝代/国家:目录里带起止年、但不属于宏观分块的细分朝代(战国·齐/西汉/东汉…),
// 加上与宏观分块时间重叠的自定义带年份朝代 —— 这些与宏观分块时间重叠,默认只展示宏观分块,
// 细分/自定义朝代由用户点亮(点亮时自动熄灭重叠的宏观分块)。
export function defaultUnlitDynastyNames(
  custom: { name: string; start_year: number | null; end_year: number | null }[] = [],
): string[] {
  const broad = new Set(TIMELINE_BANDS.map((b) => b.name))
  const names = DYNASTY_CATALOG.filter((d) => d.s != null && d.e != null && !broad.has(d.name)).map((d) => d.name)
  for (const c of custom) {
    if (c.start_year == null || broad.has(c.name)) continue
    const s = c.start_year
    const r = { s, e: c.end_year != null ? Math.max(s, c.end_year) : s }
    if (TIMELINE_BANDS.some((b) => rangesOverlap(r, b))) names.push(c.name)
  }
  return names
}

// 区间文字:"前475–前221"(单年份只显示一次)。
export function rangeLabel(r: TimeRange | null | undefined): string {
  if (!r) return ''
  return r.s === r.e ? yrFmt(r.s) : `${yrFmt(r.s)}–${yrFmt(r.e)}`
}
