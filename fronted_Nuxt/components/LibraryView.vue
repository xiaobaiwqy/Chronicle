<script setup lang="ts">
// 库:人物库 + 事件库双栏,批量管理(新增 / 编辑 / 删除)。
// 复用 .ap-* 表单体系(字段、胶囊输入、下拉、多选、取色、头像库等全局样式与组件)。
import type { ChronicleEvent, Person, SelectOption } from '~/types/chronicle'
import { dynastyColor, dynastyOptions, parseYear, yrRange } from '~/utils/dynasty'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'changed'): void }>()

const { persons, create: createPerson, update: updatePerson, remove: removePerson } = usePersons()
const { events, create: createEvent, update: updateEvent, remove: removeEvent } = useEvents()
const { dynasties, ensure } = useDynasties()
const { urlFor } = useAvatars()
const toast = useToast()

// —— 打开/关闭:回到列表态,不保留上次未完成表单 ——
watch(
  () => props.open,
  (on) => {
    if (!on) {
      pMode.value = 'list'
      eMode.value = 'list'
      delTarget.value = null
    }
  },
)

// ============================================================
// 人物库
// ============================================================
const pMode = ref<'list' | 'add' | 'edit'>('list')
const pEditId = ref<number | null>(null)
const pSaving = ref(false)
const pForm = reactive({
  name: '',
  dynasty: '战国',
  identities: [] as string[],
  birth: '',
  death: '',
  summary: '',
  avatar: '',
  color: '',
  secondaryDynasties: [] as string[],
})

const dynOptions = computed(() => dynastyOptions(persons.value, dynasties.value))
const dynastySelectOptions = computed<SelectOption[]>(() =>
  dynOptions.value.map((d) => ({ value: d.name, label: d.name, color: d.color })),
)
const secondaryDynastyOptions = computed<SelectOption[]>(() =>
  dynastySelectOptions.value.filter((o) => String(o.value) !== pForm.dynasty.trim()),
)
watch(
  () => pForm.dynasty,
  (d) => {
    const main = d.trim()
    if (main && pForm.secondaryDynasties.includes(main))
      pForm.secondaryDynasties = pForm.secondaryDynasties.filter((x) => x !== main)
  },
)
const pColor = computed(() => pForm.color || dynastyColor(pForm.dynasty.trim()))
const nameDup = computed(() => {
  const n = pForm.name.trim()
  return !!n && persons.value.some((p) => p.id !== pEditId.value && p.name.trim() === n)
})

// 头像:上传 / 姓名首字 / 头像库
const avatarInput = ref<HTMLInputElement | null>(null)
const avOpen = ref(false)
const avatarPreview = computed(() => pForm.avatar || urlFor(pForm.name.trim()))
function pickAvatar() {
  avatarInput.value?.click()
}
function onAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    toast.show('请选择图片文件')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    toast.show('图片请小于 2MB')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    pForm.avatar = String(reader.result)
  }
  reader.readAsDataURL(file)
  input.value = ''
}
function onPickLibrary(url: string) {
  pForm.avatar = url
  avOpen.value = false
}

function openAddPerson() {
  resetPerson()
  pEditId.value = null
  pMode.value = 'add'
}
function openEditPerson(p: Person) {
  pEditId.value = p.id
  pForm.name = p.name
  pForm.dynasty = p.dynasty
  pForm.identities = (p.identity || '').split('、').filter(Boolean)
  pForm.birth = p.birth_year != null ? String(p.birth_year) : ''
  pForm.death = p.death_year != null ? String(p.death_year) : ''
  pForm.summary = p.summary || ''
  pForm.color = p.color || ''
  pForm.avatar = p.avatar || ''
  pForm.secondaryDynasties = [...(p.secondary_dynasties || [])]
  pMode.value = 'edit'
}
function resetPerson() {
  pForm.name = ''
  pForm.dynasty = '战国'
  pForm.identities = []
  pForm.birth = ''
  pForm.death = ''
  pForm.summary = ''
  pForm.avatar = ''
  pForm.color = ''
  pForm.secondaryDynasties = []
}
async function savePerson() {
  if (!pForm.name.trim()) {
    toast.show('请填写姓名')
    return
  }
  const name = pForm.name.trim()
  if (persons.value.some((p) => p.id !== pEditId.value && p.name.trim() === name)) {
    toast.show('已存在同名人物')
    return
  }
  const dynasty = pForm.dynasty.trim()
  const secondaryDynasties = pForm.secondaryDynasties.filter((d) => d !== dynasty)
  const payload = {
    name,
    dynasty,
    secondary_dynasties: secondaryDynasties,
    identity: pForm.identities.join('、'),
    birth_year: pForm.birth === '' ? null : Number(pForm.birth),
    death_year: pForm.death === '' ? null : Number(pForm.death),
    summary: pForm.summary.trim(),
    color: pForm.color,
    avatar: pForm.avatar,
  }
  pSaving.value = true
  try {
    await ensure([dynasty, ...secondaryDynasties])
    if (pEditId.value != null) await updatePerson(pEditId.value, payload)
    else await createPerson(payload)
    toast.show('已保存')
    pMode.value = 'list'
    emit('changed')
  } catch (err) {
    console.error('[Chronicle] 保存人物失败', err)
    toast.show('保存失败,请检查后端服务')
  } finally {
    pSaving.value = false
  }
}

// ============================================================
// 事件库
// ============================================================
const eMode = ref<'list' | 'add' | 'edit'>('list')
const eEditId = ref<number | null>(null)
const eSaving = ref(false)
const evForm = reactive({
  title: '',
  year: '',
  desc: '',
  participants: [] as { person_id: number; role: string }[],
})

const personOptions = computed<SelectOption[]>(() =>
  persons.value.map((p) => ({ value: p.id, label: p.name, color: p.color || dynastyColor(p.dynasty) })),
)
const evDynasty = computed(() => {
  const first = evForm.participants.find((x) => x.person_id)
  return persons.value.find((p) => p.id === first?.person_id)?.dynasty ?? ''
})

function openAddEvent() {
  resetEvent()
  eEditId.value = null
  eMode.value = 'add'
}
function openEditEvent(e: ChronicleEvent) {
  eEditId.value = e.id
  evForm.title = e.title
  evForm.year = e.year_start != null ? (e.year_approx ? '~' : '') + String(e.year_start) : ''
  evForm.desc = e.description || ''
  evForm.participants = e.participants.map((p) => ({ person_id: p.person_id, role: p.role || '参与' }))
  eMode.value = 'edit'
}
function resetEvent() {
  evForm.title = ''
  evForm.year = ''
  evForm.desc = ''
  evForm.participants = [{ person_id: 0, role: '' }]
}
function addParticipant() {
  evForm.participants.push({ person_id: 0, role: '' })
}
function removeParticipant(i: number) {
  evForm.participants.splice(i, 1)
}
async function saveEvent() {
  if (!evForm.title.trim()) {
    toast.show('请填写事件标题')
    return
  }
  const participants = evForm.participants
    .filter((x) => x.person_id)
    .map((x) => ({ person_id: x.person_id, role: x.role.trim() || '参与' }))
  if (!participants.length) {
    toast.show('请至少选择一名参与者')
    return
  }
  const { year: y, approx } = parseYear(evForm.year)
  eSaving.value = true
  try {
    if (eEditId.value != null) {
      await updateEvent(eEditId.value, {
        title: evForm.title.trim(),
        description: evForm.desc.trim(),
        year_start: y,
        year_end: y,
        year_approx: approx,
        dynasty: evDynasty.value,
        participants,
      })
    } else {
      await createEvent({
        title: evForm.title.trim(),
        description: evForm.desc.trim(),
        year_start: y,
        year_end: y,
        year_approx: approx,
        dynasty: evDynasty.value,
        participants,
      })
    }
    toast.show('已保存')
    eMode.value = 'list'
    emit('changed')
  } catch (err) {
    console.error('[Chronicle] 保存事件失败', err)
    toast.show('保存失败,请检查后端服务')
  } finally {
    eSaving.value = false
  }
}

// ============================================================
// 删除(二次确认)
// ============================================================
const delTarget = ref<null | { kind: 'person' | 'event'; id: number; name: string }>(null)
const deleting = ref(false)
function askDelete(kind: 'person' | 'event', id: number, name: string) {
  delTarget.value = { kind, id, name }
}
async function confirmDelete() {
  const t = delTarget.value
  if (!t) return
  deleting.value = true
  try {
    if (t.kind === 'person') await removePerson(t.id)
    else await removeEvent(t.id)
    toast.show('已删除')
    delTarget.value = null
    emit('changed')
  } catch (err) {
    console.error('[Chronicle] 删除失败', err)
    toast.show('删除失败,请检查后端服务')
  } finally {
    deleting.value = false
  }
}

// —— 卡片展示辅助 ——
function personAvatar(p: Person): string {
  return p.avatar_url || urlFor(p.name) || ''
}
function personInitial(p: Person): string {
  return p.name?.[0] || '?'
}
function eventParticipants(e: ChronicleEvent): string {
  return e.participants.map((x) => x.name).join('、')
}
const personList = computed(() =>
  [...persons.value].sort((a, b) => (a.birth_year ?? Infinity) - (b.birth_year ?? Infinity)),
)
const eventList = computed(() =>
  [...events.value].sort((a, b) => (a.year_start ?? Infinity) - (b.year_start ?? Infinity)),
)
</script>

<template>
  <div class="lib" :class="{ show: open }">
    <div class="lib-card">
      <div class="lib-hd">
        <h3 class="lib-title">库</h3>
        <span class="lib-sub">批量管理人物与事件</span>
        <button class="close" title="关闭" @click="emit('close')">✕</button>
      </div>

      <div class="lib-cols">
        <!-- 人物库 -->
        <div class="lib-col">
          <div class="lib-col-hd">
            <span class="lib-col-title">人物库</span>
            <span class="lib-col-cnt">{{ persons.length }}</span>
            <button class="lib-add-btn" @click="pMode === 'list' ? openAddPerson() : (pMode = 'list')">
              <template v-if="pMode === 'list'">＋ 新增人物</template>
              <template v-else>返回列表</template>
            </button>
          </div>

          <div class="lib-list">
            <!-- 新增 / 编辑人物表单 -->
            <div v-if="pMode !== 'list'" class="lib-form">
              <div class="ap-name-row">
                <div class="ap-field">
                  <label>姓名</label>
                  <input v-model="pForm.name" class="ap-inp" :class="{ err: nameDup }" placeholder="如 李斯" />
                  <span v-if="nameDup" class="ap-err">已存在同名人物</span>
                </div>
                <div class="ap-av-wrap">
                  <label class="ap-av-lab">头像</label>
                  <div class="ap-av-ic">
                    <button
                      type="button"
                      class="ap-av-add"
                      :class="{ hasimg: !!avatarPreview, hasname: !avatarPreview && !!pForm.name.trim() }"
                      title="选择头像"
                      @click="avOpen = true"
                    >
                      <img v-if="avatarPreview" :src="avatarPreview" alt="头像" />
                      <span v-else-if="pForm.name.trim()" class="ap-av-char">{{ pForm.name.trim()[0] }}</span>
                      <span v-else class="ap-av-plus">+</span>
                    </button>
                    <button v-if="pForm.avatar" type="button" class="ap-av-x" title="移除头像" @click="pForm.avatar = ''">✕</button>
                  </div>
                  <input ref="avatarInput" type="file" accept="image/*" class="ap-av-file" @change="onAvatarFile" />
                  <AvatarLibrary :open="avOpen" @close="avOpen = false" @select="onPickLibrary" @upload="pickAvatar" />
                </div>
              </div>

              <div class="ap-field">
                <label>身份</label>
                <AppTagInput v-model="pForm.identities" placeholder="输入身份,回车添加" />
              </div>

              <div class="ap-field">
                <label>主朝代 / 国家</label>
                <div class="ap-dyn-row">
                  <AppSelect
                    v-model="pForm.dynasty"
                    :options="dynastySelectOptions"
                    placeholder="选择朝代 / 国家"
                    searchable
                    allow-custom
                    search-placeholder="搜索或输入朝代 / 国家…"
                  />
                  <div class="ap-color-wrap">
                    <ColorPicker :model-value="pColor" @update:model-value="pForm.color = $event" />
                    <button v-if="pForm.color" type="button" class="ap-av-x" title="恢复朝代默认色" @click="pForm.color = ''">✕</button>
                  </div>
                </div>
              </div>

              <div class="ap-field">
                <label>次朝代 / 国家 <span class="ap-opt">(可多选)</span></label>
                <AppMultiSelect
                  v-model="pForm.secondaryDynasties"
                  :options="secondaryDynastyOptions"
                  placeholder="选择次要朝代 / 国家"
                  searchable
                  allow-custom
                  search-placeholder="搜索或输入朝代 / 国家…"
                />
              </div>

              <div class="ap-pair">
                <div class="ap-field">
                  <label>生年</label>
                  <NumberStepper v-model="pForm.birth" placeholder="如 –280" />
                </div>
                <div class="ap-field">
                  <label>卒年</label>
                  <NumberStepper v-model="pForm.death" placeholder="如 –208" />
                </div>
              </div>

              <div class="ap-field">
                <label>简介</label>
                <textarea v-model="pForm.summary" class="ap-inp" placeholder="一句话记住 TA…"></textarea>
              </div>

              <div class="f-row lib-form-ft">
                <button class="btn primary sm" :disabled="pSaving" @click="savePerson">{{ pSaving ? '保存中…' : '保存' }}</button>
                <button class="btn ghost sm" @click="pMode = 'list'">取消</button>
              </div>
            </div>

            <!-- 人物卡片列表 -->
            <template v-else>
              <div v-for="p in personList" :key="'p' + p.id" class="lib-card-item">
                <div class="lib-av" :style="{ background: dynastyColor(p.dynasty) }">
                  <img v-if="personAvatar(p)" :src="personAvatar(p)" alt="" />
                  <span v-else>{{ personInitial(p) }}</span>
                </div>
                <div class="lib-info">
                  <div class="lib-nm">{{ p.name }}</div>
                  <div class="lib-meta">
                    <span class="lib-dyn" :style="{ color: dynastyColor(p.dynasty) }">{{ p.dynasty }}</span>
                    <span v-for="d in p.secondary_dynasties" :key="d" class="lib-dyn dim">{{ d }}</span>
                    <span class="lib-yrs">{{ yrRange(p.birth_year, p.death_year) }}</span>
                  </div>
                </div>
                <div class="lib-act">
                  <button type="button" class="mini-edit" title="编辑" @click="openEditPerson(p)">✎</button>
                  <button type="button" class="mini-del" title="删除" @click="askDelete('person', p.id, p.name)">✕</button>
                </div>
              </div>
              <span v-if="!personList.length" class="empty">暂无人物</span>
            </template>
          </div>
        </div>

        <!-- 事件库 -->
        <div class="lib-col">
          <div class="lib-col-hd">
            <span class="lib-col-title">事件库</span>
            <span class="lib-col-cnt">{{ events.length }}</span>
            <button class="lib-add-btn" @click="eMode === 'list' ? openAddEvent() : (eMode = 'list')">
              <template v-if="eMode === 'list'">＋ 新增事件</template>
              <template v-else>返回列表</template>
            </button>
          </div>

          <div class="lib-list">
            <!-- 新增 / 编辑事件表单 -->
            <div v-if="eMode !== 'list'" class="lib-form">
              <div class="ap-field">
                <label>事件标题</label>
                <input v-model="evForm.title" class="ap-inp" placeholder="如 长平之战" />
              </div>
              <div class="ap-field">
                <label>年份(可不填)</label>
                <input v-model="evForm.year" class="ap-inp" placeholder="如 –260 或 ~-260" />
                <div class="ap-hint">负数表示公元前,如 –260 = 前 260 年;加 ~ 或「约」表示约略年份</div>
              </div>

              <div class="ap-field">
                <label>参与者</label>
                <div class="lib-part-row" v-for="(pt, i) in evForm.participants" :key="i">
                  <AppSelect v-model="pt.person_id" :options="personOptions" placeholder="选择人物" />
                  <input v-model="pt.role" class="ap-inp lib-part-role" placeholder="定位,如 主将" />
                  <button type="button" class="mini-del" title="移除参与者" :disabled="evForm.participants.length <= 1" @click="removeParticipant(i)">✕</button>
                </div>
                <button type="button" class="lib-add-part" @click="addParticipant">＋ 添加参与者</button>
              </div>

              <div class="ap-field">
                <label>简述</label>
                <textarea v-model="evForm.desc" class="ap-inp" placeholder="发生了什么…"></textarea>
              </div>

              <div class="f-row lib-form-ft">
                <button class="btn primary sm" :disabled="eSaving" @click="saveEvent">{{ eSaving ? '保存中…' : '保存' }}</button>
                <button class="btn ghost sm" @click="eMode = 'list'">取消</button>
              </div>
            </div>

            <!-- 事件卡片列表 -->
            <template v-else>
              <div v-for="e in eventList" :key="'e' + e.id" class="lib-card-item">
                <div class="lib-info">
                  <div class="lib-nm">{{ e.title }}</div>
                  <div class="lib-meta">
                    <span class="lib-yrs">{{ yrRange(e.year_start, e.year_end, e.year_approx) }}</span>
                    <span v-if="e.participants.length" class="lib-parts">{{ eventParticipants(e) }}</span>
                  </div>
                </div>
                <div class="lib-act">
                  <button type="button" class="mini-edit" title="编辑" @click="openEditEvent(e)">✎</button>
                  <button type="button" class="mini-del" title="删除" @click="askDelete('event', e.id, e.title)">✕</button>
                </div>
              </div>
              <span v-if="!eventList.length" class="empty">暂无事件</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除二次确认 -->
    <div v-if="delTarget" class="lib-confirm">
      <div class="lib-confirm-body">
        <div class="lib-confirm-msg">确定删除{{ delTarget.kind === 'person' ? '人物' : '事件' }}「{{ delTarget.name }}」吗?</div>
        <div v-if="delTarget.kind === 'person'" class="lib-confirm-sub">将同时删除其关联的事件参与与关系。</div>
        <div class="f-row">
          <button class="btn danger" :disabled="deleting" @click="confirmDelete">{{ deleting ? '删除中…' : '确认删除' }}</button>
          <button class="btn ghost" @click="delTarget = null">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>
