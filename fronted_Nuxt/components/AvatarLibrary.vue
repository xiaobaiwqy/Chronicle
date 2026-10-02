<script setup lang="ts">
import type { AvatarOption } from '~/types/chronicle'

// 默认头像库弹层:搜索 + 缩略图网格,点击选择。用于「从库里选头像」。
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'select', url: string): void; (e: 'upload'): void }>()

const { avatars, fetchAll } = useAvatars()
const query = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

const filtered = computed<AvatarOption[]>(() => {
  const q = query.value.trim()
  if (!q) return avatars.value
  return avatars.value.filter((a) => a.name.includes(q))
})

// 打开时加载一次(useState 缓存,重复打开不重复请求),并聚焦搜索框
watch(
  () => props.open,
  async (on) => {
    if (!on) return
    query.value = ''
    if (!avatars.value.length) {
      try {
        await fetchAll()
      } catch (err) {
        console.error('[Chronicle] 头像库加载失败', err)
      }
    }
    nextTick(() => inputEl.value?.focus())
  },
)

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="avlib" @click.self="emit('close')" @keydown="onKeydown">
      <div class="avlib-card">
        <div class="avlib-hd">
          <input
            ref="inputEl"
            v-model="query"
            class="avlib-search"
            type="text"
            placeholder="搜索人物名…"
          />
          <button class="avlib-close" title="关闭" @click="emit('close')">✕</button>
        </div>
        <div class="avlib-grid">
          <button type="button" class="avlib-item" title="上传自定义头像" @click="emit('upload')">
            <span class="avlib-upload-ic">+</span>
            <span>自定义</span>
          </button>
          <button
            v-for="a in filtered"
            :key="a.name"
            class="avlib-item"
            :title="a.name"
            @click="emit('select', a.url)"
          >
            <img :src="a.url" :alt="a.name" loading="lazy" />
            <span>{{ a.name }}</span>
          </button>
        </div>
        <div v-if="filtered.length === 0" class="avlib-empty">无匹配头像</div>
      </div>
    </div>
  </Teleport>
</template>
