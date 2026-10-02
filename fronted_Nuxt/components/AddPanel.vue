<script setup lang="ts">
import type { Person, SelectOption } from '~/types/chronicle'
import { dynastyColor, dynastyOptions, parseYear } from '~/utils/dynasty'

const props = defineProps<{ open: boolean; persons: Person[] }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()

const { create: createPerson } = usePersons()
const { createRelation } = useRelations()
const { create: createEvent } = useEvents()
const { dynasties, ensure } = useDynasties()
const { urlFor } = useAvatars()
const toast = useToast()

const submitting = ref(false)
const tab = ref<'person' | 'rel' | 'event'>('person')
const tabIndex = computed(() => (tab.value === 'person' ? 0 : tab.value === 'rel' ? 1 : 2))

// 三面板轨道:translateX 随当前 tab 左右滑动(点击切换,带过渡动画)
const trackStyle = computed(() => ({ transform: `translateX(${-tabIndex.value * 100}%)` }))

// —— 顶部 tab 指示块:跟随当前 tab 的位置/宽度平滑滑动 ——
const tabsEl = ref<HTMLElement | null>(null)
const tabInd = reactive({ offset0: 0, width: 0, step: 0 })
function updateTabInd() {
  const el = tabsEl.value
  if (!el) return
  const btns = el.querySelectorAll<HTMLElement>('.ap-tab')
  if (btns.length < 2) return
  tabInd.offset0 = btns[0].offsetLeft
  tabInd.width = btns[0].offsetWidth
  tabInd.step = btns[1].offsetLeft - btns[0].offsetLeft
}
// 指示块位置 = 当前 tab 基准位,由 tabIndex 直接算出
const tabIndLeft = computed(() => tabInd.offset0 + tabIndex.value * tabInd.step)
onMounted(() => {
  nextTick(updateTabInd)
  window.addEventListener('resize', updateTabInd)
})
onBeforeUnmount(() => window.removeEventListener('resize', updateTabInd))

// —— 方向切换:→(单向正) / ←(单向反) / —(双向) 循环 ——
const DIR_ICONS = ['→', '←', '—']
const P_REL_LABELS = ['TA → 对方', '对方 → TA', '无方向(双向)']
const R_REL_LABELS = ['A → B', 'B → A', '无方向(双向)']
function cycleDir(d: number) {
  return (d + 1) % 3
}

// 打开时回到"人物"面板;关闭时收起折叠区,避免下次打开残留状态
watch(
  () => props.open,
  (val) => {
    if (val) {
      tab.value = 'person'
      // 每次打开都清空三个表单,不保留上次未编辑完的内容
      resetPerson()
      rForm.a = 0
      rForm.b = 0
      rForm.label = ''
      rForm.dir = 0
      eForm.person = 0
      eForm.role = ''
      eForm.title = ''
      eForm.year = ''
      eForm.desc = ''
    } else {
      pRelOpen.value = false
      avOpen.value = false
    }
  },
)

// —— 添加人物 ——
const pForm = reactive({ name: '', dynasty: '战国', identities: [] as string[], birth: '', death: '', summary: '', avatar: '', color: '', secondaryDynasties: [] as string[] })
const dynOptions = computed(() => dynastyOptions(props.persons, dynasties.value))

// 下拉选框数据(项目内置 AppSelect 使用);朝代支持搜索 + 直接输入自定义值
const dynastySelectOptions = computed<SelectOption[]>(() =>
  dynOptions.value.map((d) => ({ value: d.name, label: d.name, color: d.color })),
)
// 次朝代选项 = 完整目录,排除已选主朝代(避免主次重复同一项)
const secondaryDynastyOptions = computed<SelectOption[]>(() =>
  dynastySelectOptions.value.filter((o) => String(o.value) !== pForm.dynasty.trim()),
)
// 主朝代变化时,从次朝代里移除同名项,保持主次不重复
watch(
  () => pForm.dynasty,
  (d) => {
    const main = d.trim()
    if (main && pForm.secondaryDynasties.includes(main))
      pForm.secondaryDynasties = pForm.secondaryDynasties.filter((x) => x !== main)
  },
)
const personOptions = computed<SelectOption[]>(() =>
  props.persons.map((p) => ({ value: p.id, label: p.name, color: p.color || dynastyColor(p.dynasty) })),
)
// 姓名重名实时校验:输入完名字即提示并标红,不必等保存
const nameDup = computed(() => {
  const n = pForm.name.trim()
  return !!n && props.persons.some((p) => p.name.trim() === n)
})

// 头像:上传图片,否则回退到姓名首字
const avatarInput = ref<HTMLInputElement | null>(null)
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
  input.value = '' // 允许重复选择同一文件
}

// 默认头像库:弹层里选择,或按名自动匹配
const avOpen = ref(false)
const avatarPreview = computed(() => pForm.avatar || urlFor(pForm.name.trim()))
function onPickLibrary(url: string) {
  pForm.avatar = url
  avOpen.value = false
}

// 颜色:默认跟随朝代,可手动覆盖(取色面板见 ColorPicker 组件)
const pColor = computed(() => pForm.color || dynastyColor(pForm.dynasty.trim()))

// 顺手加一条关系(可选,折叠区)
const personPane = ref<HTMLElement | null>(null)
const pRelOpen = ref(false)
const pRel = reactive({ to: 0, label: '', dir: 0 }) // dir: 0=→ 1=← 2=—

function toggleRelSec() {
  pRelOpen.value = !pRelOpen.value
  if (pRelOpen.value) {
    // 展开与下滑同步:展开动画(0.28s)期间逐帧滚到底,而不是等动画结束再滚
    const start = performance.now()
    const dur = 320
    const follow = (now: number) => {
      const el = personPane.value
      if (el) el.scrollTop = el.scrollHeight
      if (now - start < dur) requestAnimationFrame(follow)
    }
    requestAnimationFrame(follow)
  }
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
  pRel.to = 0
  pRel.label = ''
  pRel.dir = 0
  pRelOpen.value = false
}

async function submitPerson() {
  if (!pForm.name.trim()) {
    toast.show('请填写姓名')
    return
  }
  const name = pForm.name.trim()
  if (props.persons.some((p) => p.name.trim() === name)) {
    toast.show('已存在同名人物')
    return
  }
  const dynasty = pForm.dynasty.trim()
  // 提交时兜底过滤:次朝代剔除与主朝代重复的项
  const secondaryDynasties = pForm.secondaryDynasties.filter((d) => d !== dynasty)
  submitting.value = true
  try {
    await ensure([dynasty, ...secondaryDynasties])
    const created = await createPerson({
      name,
      dynasty,
      secondary_dynasties: secondaryDynasties,
      identity: pForm.identities.join('、'),
      birth_year: pForm.birth === '' ? null : Number(pForm.birth),
      death_year: pForm.death === '' ? null : Number(pForm.death),
      summary: pForm.summary.trim(),
      color: pForm.color,
      avatar: pForm.avatar,
    })
    // 若折叠区里选了已有人物,顺手建立一条关系
    if (pRel.to) {
      const directed = pRel.dir !== 2
      const fromId = pRel.dir === 1 ? pRel.to : created.id
      const toId = pRel.dir === 1 ? created.id : pRel.to
      await createRelation({
        from_person_id: fromId,
        to_person_id: toId,
        label: pRel.label.trim() || '关联',
        directed,
      })
    }
    toast.show(pRel.to ? '已添加人物与关系' : '已添加人物')
    resetPerson()
    emit('saved')
  } catch (err) {
    console.error('[Chronicle] 添加人物失败', err)
    toast.show('添加失败,请检查后端服务')
  } finally {
    submitting.value = false
  }
}

// —— 添加关系 ——
const rForm = reactive({ a: 0, b: 0, label: '', dir: 0 }) // dir: 0=A→B 1=B→A 2=双向

async function submitRelation() {
  if (!rForm.a || !rForm.b) {
    toast.show('请选择两个人物')
    return
  }
  if (rForm.a === rForm.b) {
    toast.show('不能关联同一个人物')
    return
  }
  submitting.value = true
  try {
    const directed = rForm.dir !== 2
    const fromId = rForm.dir === 1 ? rForm.b : rForm.a
    const toId = rForm.dir === 1 ? rForm.a : rForm.b
    await createRelation({
      from_person_id: fromId,
      to_person_id: toId,
      label: rForm.label.trim() || '关联',
      directed,
    })
    toast.show('已添加关系')
    rForm.a = 0
    rForm.b = 0
    rForm.label = ''
    rForm.dir = 0
    emit('saved')
  } catch (err) {
    console.error('[Chronicle] 添加关系失败', err)
    toast.show('添加失败,请检查后端服务')
  } finally {
    submitting.value = false
  }
}

// —— 记一条 ——
const eForm = reactive({ person: 0, role: '', title: '', year: '', desc: '' })
const eventDynasty = computed(() => props.persons.find((p) => p.id === eForm.person)?.dynasty ?? '')

async function submitEvent() {
  if (!eForm.person) {
    toast.show('请选择参与者')
    return
  }
  if (!eForm.title.trim()) {
    toast.show('请填写事件标题')
    return
  }
  const { year: y, approx } = parseYear(eForm.year)
  submitting.value = true
  try {
    await createEvent({
      title: eForm.title.trim(),
      description: eForm.desc.trim(),
      year_start: y,
      year_end: y,
      year_approx: approx,
      dynasty: eventDynasty.value,
      participants: [{ person_id: eForm.person, role: eForm.role.trim() || '参与' }],
    })
    toast.show('已记录')
    eForm.person = 0
    eForm.role = ''
    eForm.title = ''
    eForm.year = ''
    eForm.desc = ''
    emit('saved')
  } catch (err) {
    console.error('[Chronicle] 记录失败', err)
    toast.show('记录失败,请检查后端服务')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="addpanel" :class="{ show: open }">
    <div class="ap-card">
      <div class="ap-hd">
        <h3 class="ap-title">添加</h3>
        <button class="close" title="关闭" @click="emit('close')">✕</button>
      </div>

      <div ref="tabsEl" class="ap-tabs">
        <span class="ap-tab-ind" :style="{ left: tabIndLeft + 'px', width: tabInd.width + 'px' }"></span>
        <button class="ap-tab" :class="{ on: tab === 'person' }" @click="tab = 'person'">
          <svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.5" /><path d="M5 20c1.6-3.2 4-5 7-5s5.4 1.8 7 5" /></svg>
          人物
        </button>
        <button class="ap-tab" :class="{ on: tab === 'rel' }" @click="tab = 'rel'">
          <svg class="ic" viewBox="0 0 24 24"><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="12" r="2.5" /><path d="M8.5 12h7" /></svg>
          关系
        </button>
        <button class="ap-tab" :class="{ on: tab === 'event' }" @click="tab = 'event'">
          <svg class="ic" viewBox="0 0 24 24"><path d="M5 5h14v14H5z" /><path d="M9 9h6M9 13h6" /></svg>
          记一条
        </button>
      </div>

      <!-- 三面板并排,translateX 左右滑动切换 -->
      <div class="ap-panes">
        <div class="ap-track" :style="trackStyle">
          <!-- 人物 -->
          <div class="ap-pane">
            <div ref="personPane" class="ap-pane-body">
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
                  <button v-if="pForm.avatar" type="button" class="ap-av-x" title="移除头像(恢复按名自动匹配)" @click="pForm.avatar = ''">✕</button>
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

            <!-- 顺手加一条关系(可展开) -->
            <div class="ap-sec" :class="{ open: pRelOpen }">
              <div class="ap-sec-hd" @click="toggleRelSec">
                <svg class="ic" viewBox="0 0 24 24"><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="12" r="2.5" /><path d="M8.5 12h7" /></svg>
                顺手加一条关系 <span class="ap-opt">(可选)</span>
                <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
              </div>
              <div class="ap-sec-body">
                <div class="ap-sec-inner">
                  <div class="ap-field">
                    <label>关系</label>
                    <input v-model="pRel.label" class="ap-inp" placeholder="如 君臣、同门、父子" />
                  </div>
                  <div class="ap-field">
                    <label>与谁(方向)</label>
                    <div class="ap-dir-row">
                      <span class="ap-new-chip" title="新人物">新</span>
                      <button type="button" class="ap-dir-btn" :class="{ on: pRel.dir !== 2 }" @click="pRel.dir = cycleDir(pRel.dir)">
                        {{ DIR_ICONS[pRel.dir] }}
                      </button>
                      <AppSelect v-model="pRel.to" :options="personOptions" placeholder="选择已有人物" />
                    </div>
                    <span class="ap-dir-lab">{{ P_REL_LABELS[pRel.dir] }}</span>
                  </div>
                </div>
              </div>
            </div>

            </div>
            <div class="ap-pane-ft">
              <button class="ap-btn" :disabled="submitting" @click="submitPerson">{{ submitting ? '保存中…' : '保存人物' }}</button>
            </div>
          </div>

          <!-- 关系 -->
          <div class="ap-pane">
            <div class="ap-pane-body">
              <div class="ap-field">
                <label>人物</label>
              <div class="ap-dir-row">
                <AppSelect v-model="rForm.a" :options="personOptions" placeholder="人物 A" />
                <button type="button" class="ap-dir-btn" :class="{ on: rForm.dir !== 2 }" @click="rForm.dir = cycleDir(rForm.dir)">
                  {{ DIR_ICONS[rForm.dir] }}
                </button>
                <AppSelect v-model="rForm.b" :options="personOptions" placeholder="人物 B" />
              </div>
              <span class="ap-dir-lab">{{ R_REL_LABELS[rForm.dir] }}</span>
            </div>
            <div class="ap-field">
              <label>关系</label>
              <input v-model="rForm.label" class="ap-inp" placeholder="如 君臣、同门、父子" />
            </div>
            </div>
            <div class="ap-pane-ft">
              <button class="ap-btn" :disabled="submitting" @click="submitRelation">{{ submitting ? '保存中…' : '保存关系' }}</button>
            </div>
          </div>

          <!-- 记一条 -->
          <div class="ap-pane">
            <div class="ap-pane-body">
              <div class="ap-pair">
              <div class="ap-field">
                <label>参与者</label>
                <AppSelect v-model="eForm.person" :options="personOptions" placeholder="选择人物" />
              </div>
              <div class="ap-field">
                <label>定位</label>
                <input v-model="eForm.role" class="ap-inp" placeholder="如 主将" />
              </div>
            </div>
            <div class="ap-field">
              <label>标题</label>
              <input v-model="eForm.title" class="ap-inp" placeholder="如 长平之战" />
            </div>
            <div class="ap-field">
              <label>年份</label>
              <input v-model="eForm.year" class="ap-inp" placeholder="如 –260 或 ~-260" />
              <div class="ap-hint">负数表示公元前,如 –260 = 前 260 年;加 ~ 或「约」表示约略年份</div>
            </div>
            <div class="ap-field">
              <label>简述</label>
              <textarea v-model="eForm.desc" class="ap-inp" placeholder="发生了什么…"></textarea>
            </div>
            </div>
            <div class="ap-pane-ft">
              <button class="ap-btn" :disabled="submitting" @click="submitEvent">{{ submitting ? '保存中…' : '保存记录' }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
