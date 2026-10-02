<script setup lang="ts">
// 取色面板:参考 DMS「主图配色」,含「预设配色」与「自定义配色」两个面板。
// 预设 = WPS 式大正方形色板(第一行正色,下面每列该正色的渐变色阶);
// 自定义 = HSV 取色面(横向饱和度、纵向明度)+ 色相滑条 + hex 直接输入。
const props = withDefaults(defineProps<{ modelValue: string; small?: boolean }>(), { modelValue: '#0a84ff' })

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const open = ref(false)
const tab = ref<'preset' | 'custom'>('preset')
const triggerEl = ref<HTMLElement | null>(null)
const popEl = ref<HTMLElement | null>(null)
const popStyle = ref<Record<string, string>>({})

// WPS 式预设色板
const PRESET_VIVID = ['#ff3b30', '#ff9500', '#ffd60a', '#34c759', '#00c7be', '#0a84ff', '#5e5ce6', '#bf5af2', '#ff375f']
const PRESET_ROWS = [
  ['#ff6b5e', '#ffb34d', '#ffe04d', '#6fd98d', '#4fd0c0', '#4da2ff', '#8b85ff', '#d184f7', '#ff6f8f'],
  ['#ff9d8f', '#ffcf8f', '#ffec8f', '#a3e7b8', '#8fe3d8', '#8fc4ff', '#b3afff', '#e3b3fa', '#ffa3b8'],
  ['#c0342a', '#c07600', '#b3a100', '#1f7a45', '#0f766e', '#1d5bbf', '#4a45c4', '#9a3ecf', '#c92a52'],
  ['#7a1f1a', '#7a4a00', '#6f6400', '#14532d', '#0b3a3f', '#123a6b', '#2f2b80', '#66257f', '#7a1f1a'],
]

function toggle() {
  open.value = !open.value
  if (open.value) nextTick(position)
}

function pick(c: string) {
  emit('update:modelValue', c)
  open.value = false
}

function position() {
  const rect = triggerEl.value?.getBoundingClientRect()
  if (!rect) return
  const POP_W = 208
  const POP_H = 300
  const GAP = 8
  // 默认在触发块右侧弹出;右侧空间不足则翻到左侧
  let left = rect.right + GAP
  if (left + POP_W > window.innerWidth - GAP) left = rect.left - POP_W - GAP
  left = Math.min(Math.max(GAP, left), window.innerWidth - POP_W - GAP)
  let top = rect.top - 4
  if (top + POP_H > window.innerHeight - GAP) top = window.innerHeight - POP_H - GAP
  top = Math.max(GAP, top)
  popStyle.value = { position: 'fixed', left: `${left}px`, top: `${top}px` }
}

function onDocClick(e: MouseEvent) {
  const t = e.target as Node
  if (open.value && !triggerEl.value?.contains(t) && !popEl.value?.contains(t)) open.value = false
}
function onScrollOrResize() {
  if (open.value) position()
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  window.addEventListener('scroll', onScrollOrResize, true)
  window.addEventListener('resize', onScrollOrResize)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('scroll', onScrollOrResize, true)
  window.removeEventListener('resize', onScrollOrResize)
})

/* ── HSV 取色 ── */
const clamp01 = (n: number) => Math.min(1, Math.max(0, n))

function hexToHsv(hex: string): { h: number; s: number; v: number } {
  const m = hex.replace('#', '')
  const v6 = m.length === 3 ? m.split('').map((c) => c + c).join('') : m
  const r = parseInt(v6.slice(0, 2), 16) / 255
  const g = parseInt(v6.slice(2, 4), 16) / 255
  const b = parseInt(v6.slice(4, 6), 16) / 255
  if ([r, g, b].some(Number.isNaN)) return { h: 210, s: 0.8, v: 1 }
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const d = max - min
  let h = 0
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6
    else if (max === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
    h *= 60
    if (h < 0) h += 360
  }
  return { h, s: max === 0 ? 0 : d / max, v: max }
}

function hsvToHex(h: number, s: number, v: number): string {
  const c = v * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = v - c
  let r = 0
  let g = 0
  let b = 0
  if (h < 60) [r, g, b] = [c, x, 0]
  else if (h < 120) [r, g, b] = [x, c, 0]
  else if (h < 180) [r, g, b] = [0, c, x]
  else if (h < 240) [r, g, b] = [0, x, c]
  else if (h < 300) [r, g, b] = [x, 0, c]
  else [r, g, b] = [c, 0, x]
  const to = (n: number) => Math.round((n + m) * 255).toString(16).padStart(2, '0')
  return `#${to(r)}${to(g)}${to(b)}`
}

const hsv = ref(hexToHsv(props.modelValue))

// 外部改色(预设点选 / hex 输入 / 父组件改值)时同步回 HSV;自身 emit 的往返值不同步,避免拖拽回环
watch(
  () => props.modelValue,
  (val) => {
    const current = hsvToHex(hsv.value.h, hsv.value.s, hsv.value.v)
    if (val.toLowerCase() !== current.toLowerCase()) hsv.value = hexToHsv(val)
  },
)

function emitFromHsv() {
  emit('update:modelValue', hsvToHex(hsv.value.h, hsv.value.s, hsv.value.v))
}

// 通用指针拖拽:按下后跟踪 window 的移动/抬起
function trackPointer(onMove: (e: PointerEvent) => void) {
  return (e: PointerEvent) => {
    e.preventDefault()
    onMove(e)
    const move = (ev: PointerEvent) => onMove(ev)
    const up = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }
}

// 取色面:横向饱和度、纵向明度
const svRef = ref<HTMLElement | null>(null)
const onSvPointerDown = trackPointer((e) => {
  if (!svRef.value) return
  const rect = svRef.value.getBoundingClientRect()
  hsv.value.s = clamp01((e.clientX - rect.left) / rect.width)
  hsv.value.v = 1 - clamp01((e.clientY - rect.top) / rect.height)
  emitFromHsv()
})

// 色相滑条
const hueRef = ref<HTMLElement | null>(null)
const onHuePointerDown = trackPointer((e) => {
  if (!hueRef.value) return
  const rect = hueRef.value.getBoundingClientRect()
  hsv.value.h = clamp01((e.clientX - rect.left) / rect.width) * 360
  emitFromHsv()
})

// hex 直接输入
function onHexInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value.trim()
  const m = raw.match(/^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$/)
  if (!m) return
  let hex = m[1]
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('')
  emit('update:modelValue', `#${hex.toLowerCase()}`)
}
</script>

<template>
  <button ref="triggerEl" type="button" class="cp-btn" :class="{ sm: small }" :title="modelValue" @click.stop="toggle">
    <span class="cp-dot" :style="{ background: modelValue }"></span>
  </button>

  <Teleport to="body">
    <Transition name="cp-pop">
      <div v-if="open" ref="popEl" class="cp-pop" :style="popStyle">
        <div class="cp-tabs">
          <button type="button" :class="{ on: tab === 'preset' }" @click="tab = 'preset'">预设配色</button>
          <button type="button" :class="{ on: tab === 'custom' }" @click="tab = 'custom'">自定义</button>
        </div>

        <!-- 预设配色:大正方形色板 -->
        <div v-if="tab === 'preset'" class="cp-grid">
          <div class="cp-row cp-vivid">
            <button
              v-for="c in PRESET_VIVID"
              :key="c"
              type="button"
              class="cp-cell"
              :class="{ on: c.toLowerCase() === modelValue.toLowerCase() }"
              :style="{ background: c }"
              :title="c"
              @click="pick(c)"
            />
          </div>
          <div v-for="(row, i) in PRESET_ROWS" :key="i" class="cp-row">
            <button
              v-for="c in row"
              :key="c"
              type="button"
              class="cp-cell"
              :class="{ on: c.toLowerCase() === modelValue.toLowerCase() }"
              :style="{ background: c }"
              :title="c"
              @click="pick(c)"
            />
          </div>
        </div>

        <!-- 自定义配色:取色面 + 色相滑条 + hex -->
        <div v-else class="cp-custom">
          <div
            ref="svRef"
            class="cp-sv"
            :style="{ background: `hsl(${hsv.h}, 100%, 50%)` }"
            @pointerdown="onSvPointerDown"
          >
            <div class="cp-sv-white" />
            <div class="cp-sv-black" />
            <span
              class="cp-sv-thumb"
              :style="{ left: `${hsv.s * 100}%`, top: `${(1 - hsv.v) * 100}%`, background: modelValue }"
            />
          </div>
          <div ref="hueRef" class="cp-hue" @pointerdown="onHuePointerDown">
            <span
              class="cp-hue-thumb"
              :style="{ left: `${(hsv.h / 360) * 100}%`, background: `hsl(${hsv.h}, 100%, 50%)` }"
            />
          </div>
          <input class="cp-hex" :value="modelValue" spellcheck="false" @change="onHexInput" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cp-btn {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.1);
  cursor: pointer;
  display: grid;
  place-items: center;
  padding: 0;
  transition: all 0.16s;
  flex-shrink: 0;
}
.cp-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
}
.cp-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.25);
}
.cp-btn.sm{width:20px;height:20px}
.cp-btn.sm .cp-dot{width:12px;height:12px}

.cp-pop {
  z-index: 1000;
  width: 208px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  box-shadow: 0 16px 48px rgba(20, 30, 55, 0.22);
}

.cp-tabs {
  display: flex;
  padding: 1px;
  gap: 1px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(0, 0, 0, 0.04);
}
.cp-tabs button {
  flex: 1;
  height: 22px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--ink2);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}
.cp-tabs button:hover {
  color: var(--ink);
}
.cp-tabs button.on {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

.cp-grid {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.cp-row {
  display: flex;
  gap: 3px;
}
.cp-vivid {
  padding-bottom: 5px;
  margin-bottom: 2px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.cp-cell {
  width: 18px;
  height: 18px;
  flex: none;
  padding: 0;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.1s, box-shadow 0.1s;
}
.cp-cell:hover {
  transform: scale(1.15);
}
.cp-cell.on {
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--accent);
}

.cp-custom {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cp-sv {
  position: relative;
  width: 100%;
  height: 110px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  cursor: crosshair;
  overflow: hidden;
  touch-action: none;
}
.cp-sv-white,
.cp-sv-black {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.cp-sv-white {
  background: linear-gradient(to right, #fff, rgba(255, 255, 255, 0));
}
.cp-sv-black {
  background: linear-gradient(to top, #000, rgba(0, 0, 0, 0));
}
.cp-sv-thumb {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.3);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.cp-hue {
  position: relative;
  width: 100%;
  height: 12px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: linear-gradient(to right, #f00 0%, #ff0 17%, #0f0 33%, #0ff 50%, #00f 67%, #f0f 83%, #f00 100%);
  cursor: pointer;
  touch-action: none;
}
.cp-hue-thumb {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.25);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.cp-hex {
  width: 100%;
  height: 24px;
  padding: 0 8px;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  background: #fff;
  color: var(--ink);
  font-family: var(--mono);
  font-size: 11.5px;
  outline: none;
}
.cp-hex:focus {
  border-color: var(--accent);
}

.cp-pop-enter-active,
.cp-pop-leave-active {
  transition: opacity 0.14s, transform 0.14s;
}
.cp-pop-enter-from,
.cp-pop-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.98);
}
</style>
