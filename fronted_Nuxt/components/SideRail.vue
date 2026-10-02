<script setup lang="ts">
defineProps<{ modelValue: 'graph' | 'timeline' }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: 'graph' | 'timeline'): void }>()

function switchView(v: 'graph' | 'timeline') {
  emit('update:modelValue', v)
}
</script>

<template>
  <div class="rail">
    <button :class="{ on: modelValue === 'graph' }" @click="switchView('graph')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="5" r="2.6" />
        <circle cx="5" cy="19" r="2.6" />
        <circle cx="19" cy="19" r="2.6" />
        <path d="M11 7.4 6 16.7M13 7.4 18 16.7M7.6 19h8.8" />
      </svg>
      <span class="tip">关系网</span>
    </button>
    <button :class="{ on: modelValue === 'timeline' }" @click="switchView('timeline')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 12h18" />
        <path d="M12 8.5v7" />
        <circle cx="7" cy="12" r="1.4" fill="currentColor" stroke="none" />
        <circle cx="17" cy="12" r="1.4" fill="currentColor" stroke="none" />
      </svg>
      <span class="tip">时间线</span>
    </button>
  </div>
</template>
