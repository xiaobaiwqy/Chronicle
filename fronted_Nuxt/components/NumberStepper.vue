<script setup lang="ts">
// 年份等数字输入的胶囊步进框:隐藏原生方形箭头,换成一对圆润的上下按钮
import { sanitizeYearInput } from '~/utils/dynasty'

const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string }>(), { placeholder: '' })
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

function onInput(e: Event) {
  const el = e.target as HTMLInputElement
  const clean = sanitizeYearInput(el.value)
  if (clean !== el.value) el.value = clean
  emit('update:modelValue', clean)
}

// 步进(±1):保留「~」前缀与「-」负号,只对数字部分加减;空值按 0 处理(减一即 -1)。
function bump(delta: number) {
  const raw = props.modelValue
  const tilde = raw.startsWith('~') ? '~' : ''
  const rest = tilde ? raw.slice(1) : raw
  const n = rest === '' ? 0 : Number(rest)
  const base = Number.isNaN(n) ? 0 : n
  emit('update:modelValue', tilde + String(base + delta))
}
</script>

<template>
  <div class="nstep">
    <input
      class="ap-inp mono"
      type="text"
      inputmode="text"
      autocomplete="off"
      :value="modelValue"
      :placeholder="placeholder"
      @input="onInput"
    />
    <div class="nstep-btns">
      <button type="button" class="nstep-btn" title="加一" @click="bump(1)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 15 6-6 6 6" /></svg>
      </button>
      <button type="button" class="nstep-btn" title="减一" @click="bump(-1)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.nstep {
  position: relative;
}
.nstep :deep(.ap-inp) {
  padding-right: 34px;
}
.nstep-btns {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.nstep-btn {
  width: 16px;
  height: 14px;
  flex: none;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--ink3);
  cursor: pointer;
  display: grid;
  place-items: center;
  padding: 0;
  transition: color 0.14s, transform 0.14s;
}
.nstep-btn:hover {
  color: var(--ink);
}
.nstep-btn:active {
  transform: scale(0.85);
}
.nstep-btn svg {
  width: 12px;
  height: 12px;
}
</style>
