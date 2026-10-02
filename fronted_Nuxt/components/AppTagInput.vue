<script setup lang="ts">
// 标签输入框:回车把当前输入转成一个身份胶囊,排列在输入框上方,可逐个 ✕ 删除。
const props = withDefaults(
  defineProps<{
    modelValue: string[]
    placeholder?: string
  }>(),
  { modelValue: () => [], placeholder: '输入身份,回车添加' },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: string[]): void
}>()

const text = ref('')

function add() {
  const v = text.value.trim()
  if (!v) return
  text.value = ''
  if (props.modelValue.includes(v)) return
  emit('update:modelValue', [...props.modelValue, v])
}

function remove(i: number) {
  emit('update:modelValue', props.modelValue.filter((_, idx) => idx !== i))
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    add()
  } else if (e.key === 'Backspace' && !text.value && props.modelValue.length) {
    emit('update:modelValue', props.modelValue.slice(0, -1))
  }
}
</script>

<template>
  <div class="tagin">
    <div v-if="modelValue.length" class="tagin-chips">
      <span v-for="(t, i) in modelValue" :key="t" class="tagin-chip">
        <span class="tagin-lab">{{ t }}</span>
        <button type="button" class="tagin-x" title="移除" @click="remove(i)">✕</button>
      </span>
    </div>
    <input
      v-model="text"
      class="tagin-input ap-inp"
      type="text"
      :placeholder="placeholder"
      @keydown="onKeydown"
      @blur="add"
    />
  </div>
</template>
