<script setup lang="ts">
import * as THREE from 'three'
import type { GraphEdge, Person } from '~/types/chronicle'
import { dynastyColor, yrRange } from '~/utils/dynasty'

const props = defineProps<{
  nodes: Person[]
  edges: GraphEdge[]
  highlightId: number | null
  active: boolean
  dynastyFilter: string[]
  unlitDynasties: string[]
}>()
const emit = defineEmits<{
  (e: 'select-person', id: number): void
  (e: 'select-blank'): void
  (e: 'edge-dim-change', ids: number[]): void
  (e: 'clear-dynasty-filter'): void
}>()

const wrapEl = ref<HTMLElement | null>(null)
const builtReactive = ref(false)

// —— Three.js 运行态(构建后只读) ——
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let raycaster: THREE.Raycaster
let mouseV: THREE.Vector2
let pickMeshes: THREE.Mesh[] = []
let edgePickMeshes: THREE.Mesh[] = []
let nodeGroupMap: Record<number, THREE.Group> = {}
let edgeGroup: THREE.Group
let byId = new Map<number, Person>()

// 边记录(用于主题切换时重建标签 / 切换混合模式)
interface EdgeRecord {
  id: number
  from: number
  to: number
  directed: boolean
  text: string
  mesh: THREE.Mesh            // 直线 + 一体化箭头(单一 billboard 几何,逐帧面向相机)
  mat: THREE.MeshBasicMaterial
  label: THREE.Sprite
  pick: THREE.Mesh           // 隐形粗拾取盒(逐帧跟随边中点与朝向)
}
let edgeRecords: EdgeRecord[] = []

// 边几何常量:节点圆圈"视觉半径" = Sprite scale 的一半。节点 Sprite scale = R*2,故视觉半径 = R。
// 端点要停在圆圈"外沿",用视觉半径 R + 一段固定世界间隙(见 animate 内 EDGE_GAP_WORLD)。
const NODE_R = 11
// 线与箭头按"屏幕像素"定宽(不随相机远近变粗变细);每帧按边中点距离换算成世界宽度
const LINE_PX = 2          // 线宽(像素,整体变细)
const ARROW_LEN_PX = 9     // 箭头长度(像素)
const ARROW_HALF_PX = 4    // 箭头底半宽(像素)
const Z_AXIS = new THREE.Vector3(0, 0, 1)   // 拾取盒默认朝向基准(沿边方向)
const EDGE_PICK_PX = 12    // 拾取盒横截面边长(像素,便于点击细线)

// 视角状态(四元数自由轨道旋转 / 滚轮缩放,静止时缓慢自动环绕,松手带惯性)
const DEFAULT_R = 340
const FOCUS_R = 200   // 聚焦距离:点人头像后相机推进到距其这么近(透视放大,而非放大头像本身)
const Y_AXIS = new THREE.Vector3(0, 1, 0)
const IDENT_Q = new THREE.Quaternion()
let orbitQ = new THREE.Quaternion()   // 累计轨道旋转(无角度钳制、无万向锁)
let velQ = new THREE.Quaternion()     // 角速度四元数(松手后惯性衰减)
let camR = DEFAULT_R
let targetCamR = DEFAULT_R
let focusTarget = new THREE.Vector3(0, 0, 0)
let curFocus = new THREE.Vector3(0, 0, 0)

// 初始视角与原欧拉角一致:先绕世界 Y 偏航 0.9,再绕相机右方向俯仰 0.42
orbitQ.premultiply(new THREE.Quaternion().setFromAxisAngle(Y_AXIS, 0.9))
orbitQ.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0).applyQuaternion(orbitQ), -0.42))

// 初始视角常量:轨道中心(ORIGIN)/距离(DEFAULT_R)。freeOrbitQ/freeCamR 初始即等于默认机位,故"从未手动拖动过"时点空白自然退回初始视角
const ORIGIN = new THREE.Vector3(0, 0, 0)
// freeOrbitQ/freeCamR:最近一次"手动自由视角"(初始 = 默认机位;手动拖动松手 / 滚轮缩放时更新)。点空白与取消聚焦都平滑回到这里
let freeOrbitQ = new THREE.Quaternion().copy(orbitQ)
let freeCamR = DEFAULT_R

// 视角定格/恢复:离开关系网时保存当前机位,再次进入时从 reveal 机位平滑飞回它;首次进入时 saved 仍等于初始机位,故开场运镜自动飞向初始机位。
let savedOrbitQ = new THREE.Quaternion().copy(orbitQ)
let savedCamR = DEFAULT_R
let savedFocus = new THREE.Vector3(0, 0, 0)
let hasEntered = false

// 聚焦/退焦过渡动画:orbitQ 用 slerp,中心/缩放用 lerp,easeInOutCubic 缓动,可被打断
const focusAnim = {
  active: false,
  t: 0,
  dur: 700,
  fromQ: new THREE.Quaternion(),
  toQ: new THREE.Quaternion(),
  fromFocus: new THREE.Vector3(),
  toFocus: new THREE.Vector3(),
  fromR: DEFAULT_R,
  toR: DEFAULT_R,
}

// 聚焦/悬停状态:点击头像后放大居中并绕其旋转;静止超时后自动慢转
let focusedId: number | null = null
let hoveredId: number | null = null
let lastInteract = 0

// 聚焦"拎起整张网":按 BFS 关系距离把整张网分成前后层,被点者在最前,邻居依次往后
let relayoutActive = false           // 是否处于聚焦重排状态
let relayoutT = 0                     // 0..1 重排过渡进度
let relayoutFrom: Record<number, THREE.Vector3> = {}   // 起始位置
let relayoutTo: Record<number, THREE.Vector3> = {}     // 目标位置
const RELAY_DUR = 900                 // 重排动画时长 ms
const LAYER_GAP = 46                  // 每层往后的间距(世界单位)
const RING_R = 120                    // 邻居环绕被点者的半径
const RING_R2 = 200                   // 二度邻居环绕半径
const IDLE_MS = 9000                     // 待机多久后进入自动旋转(8–10 秒)
// 待机自转:偏航匀速慢转(90 秒一圈)+ 俯仰小幅正弦起伏,方向平滑、无突变
const AUTO_YAW_SPEED = (Math.PI * 2) / 90   // 偏航角速度 rad/s
const AUTO_PITCH_AMP = 0.18                  // 俯仰正弦幅度 rad
const AUTO_PITCH_PERIOD = 22                 // 俯仰起伏周期 s
let idleT = 0                                 // 待机自转累计时间(驱动俯仰相位)

// 高亮状态:人物(来自抽屉) + 朝代颜色筛选 + 手动熄灭的连线 + 事件相关人物(搜索框点亮放大)
let currentHighlightId: number | null = null
const dimmedEdges = ref<Set<number>>(new Set())
const highlightNodeIds = ref<Set<number>>(new Set())

let built = false
let rafId = 0
let down = false
let moved = 0
let lx = 0
let ly = 0
let t0 = 0
let prevNow = 0
let viewH = 1   // 画布 CSS 像素高度(把"像素定宽"换算成世界宽度用)

// 构建时的数据快照
let nodes: Person[] = []
let edges: GraphEdge[] = []

// 主题配色(暗色)
const T = {
  bg: 0x0d1117,
  labelMain: 'rgba(255,255,255,.96)',
  labelSub: 'rgba(255,255,255,.42)',
  blend: THREE.AdditiveBlending,
  edgeOp: 0.55,
  haloBase: 0.30,
} as const

// 光晕纹理:人物色的径向渐变发光圆
function makeHaloTexture(col: THREE.Color): THREE.CanvasTexture {
  const size = 256
  const c = document.createElement('canvas')
  c.width = c.height = size
  const g = c.getContext('2d')!
  const r = Math.round(col.r * 255)
  const gg = Math.round(col.g * 255)
  const b = Math.round(col.b * 255)
  const grad = g.createRadialGradient(128, 128, 0, 128, 128, 126)
  grad.addColorStop(0, `rgba(${r},${gg},${b},0.55)`)
  grad.addColorStop(0.55, `rgba(${r},${gg},${b},0.16)`)
  grad.addColorStop(1, `rgba(${r},${gg},${b},0)`)
  g.fillStyle = grad
  g.beginPath()
  g.arc(128, 128, 126, 0, Math.PI * 2)   // 裁成正圆,避免方形底在透明排序时偶尔露出
  g.fill()
  const tex = new THREE.CanvasTexture(c)
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  return tex
}

// 头像纹理:纯色圆 + 细描边 + 轻微径向渐变/内阴影(像浮在空间里的小圆牌) + 姓名首字;
// 若传入图片(自定义头像),则用图片覆盖绘制。
function drawNodeFace(p: Person, img?: HTMLImageElement): THREE.CanvasTexture {
  const size = 256
  const c = document.createElement('canvas')
  c.width = c.height = size
  const g = c.getContext('2d')!
  const cx = size / 2
  const cy = size / 2
  const r = 122
  if (img) {
    // 圆形裁切 + cover 填充图片
    g.save()
    g.beginPath()
    g.arc(cx, cy, r, 0, Math.PI * 2)
    g.clip()
    const s = Math.max((r * 2) / img.width, (r * 2) / img.height)
    const w = img.width * s
    const h = img.height * s
    g.drawImage(img, cx - w / 2, cy - h / 2, w, h)
    g.restore()
  } else {
    // 底色圆
    g.beginPath()
    g.arc(cx, cy, r, 0, Math.PI * 2)
    g.fillStyle = p.color || dynastyColor(p.dynasty)
    g.fill()
    // 轻微径向渐变:左上受光、右下略暗,增强立体感
    const dome = g.createRadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.08, cx, cy, r)
    dome.addColorStop(0, 'rgba(255,255,255,.20)')
    dome.addColorStop(0.55, 'rgba(255,255,255,0)')
    dome.addColorStop(1, 'rgba(0,0,0,.16)')
    g.beginPath()
    g.arc(cx, cy, r, 0, Math.PI * 2)
    g.fillStyle = dome
    g.fill()
    // 内圈轻微内阴影(贴近描边的一圈暗边)
    const inner = g.createRadialGradient(cx, cy, r * 0.76, cx, cy, r)
    inner.addColorStop(0, 'rgba(0,0,0,0)')
    inner.addColorStop(1, 'rgba(0,0,0,.18)')
    g.beginPath()
    g.arc(cx, cy, r, 0, Math.PI * 2)
    g.fillStyle = inner
    g.fill()
    // 姓名首字
    g.fillStyle = 'rgba(255,255,255,.97)'
    g.font = `700 ${Math.round(size * 0.5)}px 'PingFang SC','Helvetica Neue',-apple-system,sans-serif`
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    g.fillText(p.name[0], cx, cy + 2)
  }
  // 外圈细描边
  g.lineWidth = 4
  g.strokeStyle = 'rgba(255,255,255,.55)'
  g.beginPath()
  g.arc(cx, cy, r - 2, 0, Math.PI * 2)
  g.stroke()
  const tex = new THREE.CanvasTexture(c)
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  return tex
}

function makeNodeTexture(p: Person): THREE.CanvasTexture {
  return drawNodeFace(p)
}

// 自定义头像异步加载:成功后替换内层圆牌纹理
function loadNodeAvatar(p: Person, face: THREE.Sprite): void {
  const src = p.avatar_url || p.avatar
  if (!src) return
  const img = new Image()
  img.onload = () => {
    const mat = face.material as THREE.SpriteMaterial
    mat.map = drawNodeFace(p, img)
    mat.needsUpdate = true
  }
  img.src = src
}

// 白色细环纹理(悬停/聚焦时点亮)
function makeRingTexture(): THREE.CanvasTexture {
  const size = 256
  const c = document.createElement('canvas')
  c.width = c.height = size
  const g = c.getContext('2d')!
  g.strokeStyle = '#ffffff'
  g.lineWidth = 6
  g.beginPath()
  g.arc(128, 128, 122, 0, Math.PI * 2)
  g.stroke()
  const tex = new THREE.CanvasTexture(c)
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  return tex
}

// 名字标签(古典楷体,高分辨率防糊;挂在圆圈上方)
const NAME_FONT = "'Kaiti SC','STKaiti','KaiTi','Ma Kai','楷体',serif"
function makeLabel(p: Person): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = 512                    // 提高分辨率:画布放大 2 倍,避免 sprite 放大后糊
  c.height = 180
  const g = c.getContext('2d')!
  g.textAlign = 'center'
  // 人名:古典楷体
  g.font = `600 64px ${NAME_FONT}`
  g.shadowColor = 'rgba(0,0,0,.85)'
  g.shadowBlur = 10
  g.fillStyle = T.labelMain
  g.fillText(p.name, 256, 78)
  // 生卒年:小一号、素一点(monospace 保证数字对齐),略淡
  g.font = '500 30px ui-monospace,Menlo,monospace'
  g.shadowBlur = 6
  g.fillStyle = T.labelSub
  g.fillText(p.birth_year != null ? yrRange(p.birth_year, p.death_year) : '', 256, 128)
  const tex = new THREE.CanvasTexture(c)
  tex.minFilter = THREE.LinearFilter
  tex.anisotropy = 4               // 各向异性过滤,斜看时更清晰
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }))
  sp.scale.set(48, 17, 1)          // 视觉尺寸不变,但纹理分辨率翻倍 → 放大不再糊
  return sp
}

// 关系名标签(素净细灰,高分辨率)
function makeEdgeLabel(text: string): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = 256
  c.height = 96
  const g = c.getContext('2d')!
  g.textAlign = 'center'
  g.font = "400 34px 'PingFang SC','Helvetica Neue',-apple-system,sans-serif"  // 细体
  g.shadowColor = 'rgba(0,0,0,.9)'
  g.shadowBlur = 6
  g.fillStyle = 'rgba(226,232,240,.72)'        // 灰一点,退后
  g.fillText(text, 128, 52)
  const tex = new THREE.CanvasTexture(c)
  tex.minFilter = THREE.LinearFilter
  tex.anisotropy = 4
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }))
  sp.scale.set(20, 7.5, 1)         // 比之前小一点,关系名退到注解层级
  return sp
}

function buildGraph() {
  const wrap = wrapEl.value
  if (!wrap || built) return
  const W = wrap.clientWidth
  const H = wrap.clientHeight
  if (!W || !H) return
  viewH = H

  nodes = [...props.nodes]
  edges = [...props.edges]

  scene = new THREE.Scene()
  scene.background = new THREE.Color(T.bg)
  scene.fog = new THREE.Fog(T.bg, 420, 900)
  camera = new THREE.PerspectiveCamera(60, W / H, 1, 2000)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(W, H)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  wrap.appendChild(renderer.domElement)

  // 光照:让三维球有体积感(环境光打底 + 两盏方向光塑造明暗)
  scene.add(new THREE.AmbientLight(0xffffff, 0.9))
  const keyLight = new THREE.DirectionalLight(0xffffff, 1.1)
  keyLight.position.set(180, 260, 220)
  scene.add(keyLight)
  const fillLight = new THREE.DirectionalLight(0x88aaff, 0.4)
  fillLight.position.set(-220, -120, -180)
  scene.add(fillLight)

  // 环境贴图:玻璃折射(transmission)需要环境才能出"弹珠"质感。用代码现场画一个简易渐变环境,
  // 不依赖 three/examples 里的 RoomEnvironment(避免导入路径问题),失败也不阻塞渲染。
  try {
    const envScene = new THREE.Scene()
    const grad = new THREE.Mesh(
      new THREE.SphereGeometry(100, 16, 16),
      new THREE.MeshBasicMaterial({ side: THREE.BackSide, vertexColors: true }),
    )
    // 给环境球从上到下做个亮→暗的渐变,让玻璃有反射层次
    const posAttr = grad.geometry.getAttribute('position')
    const cols: number[] = []
    for (let i = 0; i < posAttr.count; i++) {
      const y = posAttr.getY(i) / 100           // -1..1
      const v = 0.35 + Math.max(0, y) * 0.65     // 上亮下暗
      cols.push(v, v, v * 1.02)
    }
    grad.geometry.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3))
    envScene.add(grad)
    const pmrem = new THREE.PMREMGenerator(renderer)
    scene.environment = pmrem.fromScene(envScene, 0.04).texture
    pmrem.dispose()
  } catch (err) {
    console.warn('环境贴图生成失败,玻璃将退化为纯光照', err)
  }

  // 布局:按朝代(国家)聚类 —— 同朝代人物聚成更紧密的小群,不同朝代分占圆周不同扇区
  const groups = new Map<string, Person[]>()
  nodes.forEach((p) => {
    const key = (p.dynasty || '未知').trim() || '未知'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(p)
  })
  const dynNames = [...groups.keys()]
  const sectorCount = Math.max(1, dynNames.length)
  const pos: Record<number, THREE.Vector3> = {}
  const baseR = 150
  let di = 0
  groups.forEach((members) => {
    const baseAngle = (di / sectorCount) * Math.PI * 2 + 0.35
    const spread = Math.min(0.42, (Math.PI * 2 / sectorCount) * 0.32)
    members.forEach((p, mi) => {
      const off = members.length <= 1 ? 0 : (mi / (members.length - 1) - 0.5) * 2 * spread
      const a = baseAngle + off
      const r = baseR + (mi % 3) * 30
      const y = ((di * 53 + mi * 31) % 110) - 55
      pos[p.id] = new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r)
    })
    di++
  })
  byId = new Map(nodes.map((p) => [p.id, p]))

  // 关系边:直线 + 一体化箭头(单一 billboard 几何,线端/箭头尖搭在圆圈边缘)
  edgeGroup = new THREE.Group()
  scene.add(edgeGroup)
  const t = T
  edges.forEach((r) => {
    const a = pos[r.from]
    const b = pos[r.to]
    if (!a || !b) return
    const fromPerson = byId.get(r.from)
    const toPerson = byId.get(r.to)
    const colA = new THREE.Color(fromPerson ? dynastyColor(fromPerson.dynasty) : '#8e8e93')
    const colB = new THREE.Color(toPerson ? dynastyColor(toPerson.dynasty) : '#8e8e93')
    const directed = r.directed !== false
    // 单一几何:有向 = 线梯形 + 箭头三角(5 顶点);无向 = 矩形线(4 顶点),索引固定
    const vCount = directed ? 5 : 4
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vCount * 3), 3))
    // 顶点色:两端各取所属人物的朝代色;同色退化为纯色,异色沿线做 A→B 双色渐变
    const vCol = new Float32Array(vCount * 3)
    const setVC = (i: number, c: THREE.Color) => { vCol[i * 3] = c.r; vCol[i * 3 + 1] = c.g; vCol[i * 3 + 2] = c.b }
    if (directed) {
      setVC(0, colA); setVC(1, colA)
      setVC(2, colB); setVC(3, colB); setVC(4, colB)
    } else {
      setVC(0, colA); setVC(1, colA)
      setVC(2, colB); setVC(3, colB)
    }
    geo.setAttribute('color', new THREE.BufferAttribute(vCol, 3))
    geo.setIndex(directed ? [0, 1, 3, 0, 3, 2, 2, 3, 4] : [0, 1, 3, 0, 3, 2])
    // 连线做深度测试(depthTest:true):会被"写了深度的头像"在像素级真实地挡住——圆圈在前就压着线,远近关系正确
    const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, vertexColors: true, transparent: true, opacity: t.edgeOp, blending: t.blend, depthWrite: false, depthTest: true, side: THREE.DoubleSide })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.userData = { id: r.id, from: r.from, to: r.to }
    mesh.frustumCulled = false        // 逐帧改写顶点并移动位置,关闭视锥剔除避免误裁
    edgeGroup.add(mesh)

    // 隐形的粗拾取盒(每帧跟随边中点与朝向,便于点击细连线)
    const pickMat = new THREE.MeshBasicMaterial()
    pickMat.visible = false
    const pick = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), pickMat)
    pick.userData = { id: r.id, from: r.from, to: r.to }
    edgeGroup.add(pick)
    edgePickMeshes.push(pick)

    const lab = makeEdgeLabel(r.label)
    const mp = a.clone().add(b).multiplyScalar(0.5)
    lab.position.set(mp.x, mp.y + 5, mp.z)
    edgeGroup.add(lab)
    edgeRecords.push({ id: r.id, from: r.from, to: r.to, directed, text: r.label, mesh, mat, label: lab, pick })
  })

  // 人物节点:玻璃弹珠外壳(三维、透明、有折射体积感) 包住 内层二维圆牌(首字/照片,始终朝前)
  nodes.forEach((p) => {
    const grp = new THREE.Group()
    grp.position.copy(pos[p.id])
    grp.userData.basePos = pos[p.id].clone()   // 当前基准位置(聚焦重排会更新它)
    grp.userData.homePos = pos[p.id].clone()   // 原始布局位置(永不改写,退焦复原用)
    const col = new THREE.Color(p.color || dynastyColor(p.dynasty))
    const R = 11

    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeHaloTexture(col), transparent: true, opacity: t.haloBase, blending: t.blend, depthWrite: false }))
    const haloBase = R * 3.4
    halo.scale.set(haloBase, haloBase, 1)
    grp.add(halo)

    // 内部二维圆头像:不透明实心圆牌,写深度 → 真实地挡住从它身后穿过的线(第 1 条:不让线透到头像上面)。
    // alphaTest 丢弃圆外像素,避免 Sprite 方形平面四角误写深度切出方框。
    const face = new THREE.Sprite(new THREE.SpriteMaterial({
      map: makeNodeTexture(p),
      transparent: false,          // 不透明:身后线条被这块实心圆牌挡住,不再交叠穿透
      depthTest: true,
      depthWrite: true,            // 写深度,成为"空间里的实心遮挡板"
      alphaTest: 0.5,              // 圆外透明像素丢弃,不写深度
    }))
    face.scale.set(R * 1.4, R * 1.4, 1)
    grp.add(face)

    const ring = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeRingTexture(), transparent: true, opacity: 0, depthWrite: false }))
    const ringBase = R * 1.8
    ring.scale.set(ringBase, ringBase, 1)
    grp.add(ring)

    const lab = makeLabel(p)
    lab.position.y = R + 5
    grp.add(lab)

    const pickMat = new THREE.MeshBasicMaterial()
    pickMat.visible = false
    const pick = new THREE.Mesh(new THREE.SphereGeometry(R, 10, 10), pickMat)
    pick.userData.pid = p.id
    grp.add(pick)
    pickMeshes.push(pick)

    grp.userData.face = face          // 内嵌二维圆牌(首字/照片,始终朝前)
    loadNodeAvatar(p, face)           // 有自定义头像时异步加载覆盖
    grp.userData.halo = halo
    grp.userData.ring = ring
    grp.userData.label = lab
    grp.userData.R = R
    grp.userData.linked = true
    grp.userData.haloBase = haloBase
    scene.add(grp)
    nodeGroupMap[p.id] = grp
  })

  raycaster = new THREE.Raycaster()
  mouseV = new THREE.Vector2()
  t0 = performance.now()
  prevNow = performance.now()
  lastInteract = performance.now()

  wrap.addEventListener('mousedown', onMouseDown)
  renderer.domElement.addEventListener('click', onClick)   // 点击监听绑在画布上,避免被抽屉/搜索框等 UI 误触发
  wrap.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)

  currentHighlightId = props.highlightId
  applyHighlight()

  built = true
  builtReactive.value = true
  // 首次构建且处于关系网视图时,播放开场运镜(先摆到 reveal 机位再启动过渡,避免首帧闪一下默认位)。重建(数据变化)时不重播。
  if (!hasEntered && props.active) {
    hasEntered = true
    playEntryDolly(savedOrbitQ, savedFocus, savedCamR, 1500)
  }
  animate()
}

// 拾取:把鼠标事件换算到 NDC 并射向节点拾取球 / 连线拾取盒,返回首个命中的节点与边
function pickAt(e: MouseEvent) {
  const rect = renderer.domElement.getBoundingClientRect()
  mouseV.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  mouseV.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(mouseV, camera)
  // 只对"可见"对象拾取:raycaster 不自动跳过 visible=false 的对象,须手动过滤。
  // 隐藏节点的拾取球挂在节点组下(组 visible=false),隐藏连线的拾取盒自身 visible=false。
  const visPicks = pickMeshes.filter((m) => m.parent?.visible !== false)
  const visEdgePicks = edgePickMeshes.filter((m) => m.visible !== false)
  const nodeHit = raycaster.intersectObjects(visPicks)[0]
  const edgeHit = nodeHit ? null : raycaster.intersectObjects(visEdgePicks)[0]
  return { nodeHit, edgeHit }
}

function onMouseDown(e: MouseEvent) {
  down = true
  moved = 0
  lastInteract = performance.now()
  if (focusAnim.active) {
    // 拖动打断进行中的过渡:把稳态逼近目标切到本次过渡终点,改用指数逼近平滑收尾,而非让镜头被旧目标拖回
    focusTarget.copy(focusAnim.toFocus)
    targetCamR = focusAnim.toR
  }
  focusAnim.active = false   // 拖动打断进行中的聚焦过渡,交由手动旋转
  lx = e.clientX
  ly = e.clientY
}

function onMouseMove(e: MouseEvent) {
  if (down) {
    const dx = e.clientX - lx
    const dy = e.clientY - ly
    moved += Math.abs(dx) + Math.abs(dy)
    lastInteract = performance.now()
    // 偏航绕世界 Y 轴,俯仰绕相机当前右方向,四元数 premultiply 累计(无角度钳制)
    const yawQ = new THREE.Quaternion().setFromAxisAngle(Y_AXIS, -dx * 0.011)
    orbitQ.premultiply(yawQ)
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(orbitQ)
    const pitchQ = new THREE.Quaternion().setFromAxisAngle(right, -dy * 0.007)
    orbitQ.premultiply(pitchQ)
    velQ.copy(pitchQ).multiply(yawQ)   // 本帧世界系总旋转,作为松手后的惯性初速
    lx = e.clientX
    ly = e.clientY
  } else if (renderer && raycaster) {
    // 鼠标在添加面板/详情抽屉上时,不悬停/高亮关系网(避免透过面板误触背后的节点)
    const t = e.target as HTMLElement
    if (t && t.closest && (t.closest('.addpanel') || t.closest('.drawer'))) {
      hoverNode(null)
      return
    }
    const { nodeHit, edgeHit } = pickAt(e)
    wrapEl.value!.style.cursor = nodeHit || edgeHit ? 'pointer' : 'grab'
    hoverNode(nodeHit ? (nodeHit.object.userData.pid as number) : null)
  }
}

function onMouseUp() {
  down = false
  // 手动拖动松手:把当前相机姿态记为"最近一次自由视角"(点空白 / 取消聚焦都回这个视角)
  if (moved > 6 && focusedId == null) {
    freeOrbitQ.copy(orbitQ)
    freeCamR = camR
  }
}

function onClick(e: MouseEvent) {
  if (moved > 6) return
  lastInteract = performance.now()
  const { nodeHit, edgeHit } = pickAt(e)

  if (nodeHit) {
    const id = nodeHit.object.userData.pid as number
    // 再点一次同一头像取消聚焦(回到自由视角);点其它头像改道聚焦
    if (focusedId === id) {
      unfocus()
      dimmedEdges.value = new Set()
      applyHighlight()
      emit('select-blank')
    } else {
      focusPerson(id)
      dimmedEdges.value = new Set()
      applyHighlight()
      emit('select-person', id)
    }
    return
  }

  if (edgeHit) {
    const ud = edgeHit.object.userData as { id: number; from: number; to: number }
    toggleEdge(ud.id)
    applyHighlight()
    emit('select-blank')
    return
  }

  resetView()
  dimmedEdges.value = new Set()
  emit('clear-dynasty-filter')
  highlightNodeIds.value = new Set()
  applyHighlight()
  emit('select-blank')
}

function onWheel(e: WheelEvent) {
  e.preventDefault()
  lastInteract = performance.now()
  targetCamR = Math.max(150, Math.min(620, targetCamR + e.deltaY * 0.4))
  // 缩放也是手动调整:记录缩放后的自由距离,回位时保留缩放
  if (focusedId == null) freeCamR = targetCamR
}

// 聚焦"拎起整张网":以被点者为原点,按 BFS 关系距离把所有节点分成前后层并平滑飞过去。
// 被点者在原点(最前、居中),一度邻居环绕其后(LAYER_GAP),二度再往后,以此类推;退焦则飞回原布局。
function computeRelayout(focusId: number) {
  // BFS 求每个节点到 focusId 的最短关系距离
  const dist = new Map<number, number>()
  dist.set(focusId, 0)
  const queue = [focusId]
  const adj = new Map<number, number[]>()
  edges.forEach((r) => {
    if (!adj.has(r.from)) adj.set(r.from, [])
    if (!adj.has(r.to)) adj.set(r.to, [])
    adj.get(r.from)!.push(r.to)
    adj.get(r.to)!.push(r.from)
  })
  while (queue.length) {
    const cur = queue.shift()!
    const d = dist.get(cur)!
    for (const nb of adj.get(cur) || []) {
      if (!dist.has(nb)) { dist.set(nb, d + 1); queue.push(nb) }
    }
  }
  // 相机视线方向(指向场景)与右/上方向,用于在"垂直于视线"的平面里环布邻居
  const viewDir = new THREE.Vector3(0, 0, -1).applyQuaternion(orbitQ).normalize() // 相机朝向
  const right = new THREE.Vector3(1, 0, 0).applyQuaternion(orbitQ).normalize()
  const up = new THREE.Vector3(0, 1, 0).applyQuaternion(orbitQ).normalize()
  const back = viewDir.clone().negate() // 指向场景深处(离相机更远)
  // 被点者挪到"相机正对的聚焦点"ORIGIN(画面正中心、最前),邻居围绕它环布并逐层往后
  const focusPos = ORIGIN.clone()

  const layerMembers = new Map<number, number[]>()
  nodes.forEach((p) => {
    const d = dist.has(p.id) ? dist.get(p.id)! : -1   // -1 = 未连通
    if (!layerMembers.has(d)) layerMembers.set(d, [])
    layerMembers.get(d)!.push(p.id)
  })

  relayoutTo = {}
  layerMembers.forEach((ids, d) => {
    if (d === -1) {
      // 与被点者不连通:保持原始布局位置(homePos),不参与重排,不飞出视野
      ids.forEach((id) => {
        const g = nodeGroupMap[id]
        relayoutTo[id] = g ? ((g.userData.homePos as THREE.Vector3) || (g.userData.basePos as THREE.Vector3)).clone() : ORIGIN.clone()
      })
      return
    }
    if (d === 0) { relayoutTo[ids[0]] = focusPos.clone(); return }
    const depth = Math.min(d, 3) * LAYER_GAP            // 每层往后推,最多压 3 层
    const ringR = d === 1 ? RING_R : RING_R2 + (Math.min(d, 3) - 2) * 40
    ids.forEach((id, i) => {
      const a = (i / ids.length) * Math.PI * 2 + d * 0.6
      // 在垂直于视线的平面内环绕,再往后推 depth
      const p2 = focusPos.clone()
        .addScaledVector(right, Math.cos(a) * ringR)
        .addScaledVector(up, Math.sin(a) * ringR)
        .addScaledVector(back, depth)
      relayoutTo[id] = p2
    })
  })
}

function startRelayout(focusId: number | null) {
  // 记录起始位置,算目标位置,启动过渡
  relayoutFrom = {}
  nodes.forEach((p) => {
    const g = nodeGroupMap[p.id]
    relayoutFrom[p.id] = g ? g.position.clone() : new THREE.Vector3()
  })
  if (focusId != null) {
    computeRelayout(focusId)
  } else {
    // 退焦:回到各自原始布局 homePos(注意不是 basePos —— 聚焦时 basePos 已被重排改写)
    relayoutTo = {}
    nodes.forEach((p) => {
      const g = nodeGroupMap[p.id]
      relayoutTo[p.id] = g ? ((g.userData.homePos as THREE.Vector3) || (g.userData.basePos as THREE.Vector3)).clone() : new THREE.Vector3()
    })
  }
  relayoutT = 0
  relayoutActive = true
}

// 聚焦某个人物 = 相机转向 + 推进 + 整张网按关系距离重排分层(头像本身不缩放)。
function focusPerson(id: number) {
  if (!built) return
  const g = nodeGroupMap[id]
  if (!g) return
  focusedId = id
  const basePos = g.userData.basePos as THREE.Vector3
  // 目标偏移方向 = 从聚焦中心指向当前相机,稍抬高俯视;聚焦中心取原点(重排后被点者会移到原点)
  const dir = new THREE.Vector3().subVectors(camera.position, basePos)
  if (dir.lengthSq() < 1e-8) dir.set(0, 0, 1)
  dir.normalize()
  dir.y += 0.25
  dir.normalize()
  const toQ = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir)
  // 相机看向原点(重排后被点者所在),距离推进到 FOCUS_R
  startFocusAnim(toQ, ORIGIN, FOCUS_R)
  startRelayout(id)
  lastInteract = performance.now()
}

// 取消聚焦:平滑回到上一个自由视角,同时把整张网飞回原布局
function unfocus() {
  focusedId = null
  startFocusAnim(freeOrbitQ, ORIGIN, freeCamR)
  startRelayout(null)
}

// 点击空白回位:回到"最近一次手动自由视角"(拖动松手/滚轮缩放时记录;从未手动拖动过则 freeOrbitQ/freeCamR 仍是初始机位)。聚焦状态下先退焦再回位,并恢复全网布局
function resetView() {
  focusedId = null
  startFocusAnim(freeOrbitQ, ORIGIN, freeCamR, 900)
  startRelayout(null)
}

// 启动一次聚焦/退焦过渡:orbitQ 用 slerp,中心与缩放用 lerp,easeInOutCubic
function startFocusAnim(toQ: THREE.Quaternion, toFocus: THREE.Vector3, toR: number, dur = 700) {
  focusAnim.fromQ.copy(orbitQ)
  focusAnim.toQ.copy(toQ)
  focusAnim.fromFocus.copy(curFocus)
  focusAnim.toFocus.copy(toFocus)
  focusAnim.fromR = camR
  focusAnim.toR = toR
  focusAnim.dur = dur
  focusAnim.t = 0
  focusAnim.active = true
  velQ.copy(IDENT_Q)          // 清空惯性,避免与过渡动画打架
  idleT = 0                    // 重置待机自转相位,动画结束后自转计时从零开始
  // focusTarget/targetCamR 不在此处改写:它们只在过渡结束(animate 的 k>=1 分支)或拖动打断时提交,
  // 保证过渡插值与稳态指数逼近共用同一目标,避免两套更新在第一帧叠加造成"先瞬移再缓动"的跳变。
}

// 保存当前机位(离开关系网时定格,供下次进入恢复)
function saveCamera() {
  savedOrbitQ.copy(orbitQ)
  savedCamR = camR
  savedFocus.copy(curFocus)
}

// 进入运镜:从一个更远、略侧偏的 reveal 机位平滑飞入目标机位。
// 首次进入 saved 即初始机位(飞入初始定格);再次进入 saved 是上次离开时的定格机位(飞回它)。
function playEntryDolly(targetQ: THREE.Quaternion, targetFocus: THREE.Vector3, targetR: number, dur = 1300) {
  const revealQ = targetQ.clone().premultiply(new THREE.Quaternion().setFromAxisAngle(Y_AXIS, 0.38))
  orbitQ.copy(revealQ)
  camR = Math.min(targetR * 1.4, 620) // 封顶避免 reveal 距离超出用户可缩放上限,落入过浓雾区
  curFocus.copy(targetFocus)
  focusTarget.copy(targetFocus)
  targetCamR = camR
  startFocusAnim(targetQ.clone(), targetFocus.clone(), targetR, dur)
}

// 切换某条连线的亮/暗:点一下翻转,不影响其它连线
function toggleEdge(id: number) {
  const s = new Set(dimmedEdges.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  dimmedEdges.value = s
}

// 供外部(详情抽屉)高亮/取消某条关系
function toggleEdgeHighlight(id: number) {
  if (!built) return
  toggleEdge(id)
  applyHighlight()
}

function hoverNode(pid: number | null) {
  hoveredId = pid
}

// 节点高亮:事件相关人物点亮优先;其次人物一度关系 / 朝代颜色线(熄灭某条连线不影响人物本身的亮暗)
function nodeLinked(p: Person): boolean {
  if (highlightNodeIds.value.size) {
    return highlightNodeIds.value.has(p.id)
  }
  if (!currentHighlightId && !props.dynastyFilter.length) return true
  if (currentHighlightId) {
    if (p.id === currentHighlightId) return true
    // 一度邻居:与聚焦者之间的连线若被手动熄灭,则该人物也退后(取消凸显)
    if (edges.some((r) => {
      const connects = (r.from === currentHighlightId && r.to === p.id) || (r.to === currentHighlightId && r.from === p.id)
      return connects && !dimmedEdges.value.has(r.id)
    })) return true
  }
  if (props.dynastyFilter.includes(dynastyColor(p.dynasty))) return true
  return false
}

// 光晕开关:只给"高亮者"点光晕 —— 事件组/朝代组全员点亮;人物聚焦时只点聚焦者本人(邻居虽亮但无光晕,分层级)。
// 与 nodeLinked(脸牌亮暗)分离:脸牌仍按聚焦者+一度邻居点亮,光晕则更严格。
function nodeHalo(p: Person): boolean {
  if (highlightNodeIds.value.size) return highlightNodeIds.value.has(p.id)
  if (currentHighlightId != null) return p.id === currentHighlightId
  if (props.dynastyFilter.length) return props.dynastyFilter.includes(dynastyColor(p.dynasty))
  return false
}

// 连线高亮分级:0=熄灭 1=普通亮 2=主线(聚焦者直接相连)。被手动熄灭的直接灭;事件相关人物之间连线点亮;否则按人物聚焦 / 朝代颜色决定(朝代模式要求两端同朝代)
function edgeLevel(r: { id: number; from: number; to: number }): number {
  if (dimmedEdges.value.has(r.id)) return 0
  if (highlightNodeIds.value.size) {
    return highlightNodeIds.value.has(r.from) && highlightNodeIds.value.has(r.to) ? 1 : 0
  }
  if (!currentHighlightId && !props.dynastyFilter.length) return 1
  if (currentHighlightId && (r.from === currentHighlightId || r.to === currentHighlightId)) return 2
  if (props.dynastyFilter.length) {
    const fp = byId.get(r.from)
    const tp = byId.get(r.to)
    if (fp && tp && props.dynastyFilter.includes(dynastyColor(fp.dynasty)) && props.dynastyFilter.includes(dynastyColor(tp.dynasty))) return 1
  }
  return 0
}

// 人物是否"点亮"可见:按朝代标签(主 + 次)的名字判断 —— 任一标签未被熄灭即保留;
// 无标签人物始终展示。关系网与时间无关,不做时间重叠判断。
function personVisible(p: Person): boolean {
  const tags = [p.dynasty, ...(p.secondary_dynasties ?? [])].filter((n) => n && n.trim())
  if (!tags.length) return true
  return tags.some((n) => !props.unlitDynasties.includes(n))
}

function applyHighlight() {
  if (!built || !edgeGroup) return
  const op = T.edgeOp
  edgeRecords.forEach((rec) => {
    // 点亮/熄灭:连线两端人物都可见才显示该连线
    const fromP = byId.get(rec.from)
    const toP = byId.get(rec.to)
    const vis = (!fromP || personVisible(fromP)) && (!toP || personVisible(toP))
    rec.mesh.visible = vis
    rec.label.visible = vis
    rec.pick.visible = vis
    const lv = edgeLevel({ id: rec.id, from: rec.from, to: rec.to })
    rec.mat.opacity = lv === 0 ? 0.05 : (lv === 2 ? 0.9 : op)
    // 边上的关系名标签跟随线一起变暗,避免压暗的线还挂着亮白的字
    ;(rec.label as THREE.Sprite).material.opacity = lv === 0 ? 0.06 : 1
  })
  nodes.forEach((p) => {
    const g = nodeGroupMap[p.id]
    if (!g) return
    const linked = nodeLinked(p)
    g.userData.linked = linked
    // 点亮/熄灭:熄灭朝代的全部标签人物隐藏(节点组 visible=false,连同光环/标签/拾取一起消失)
    g.visible = personVisible(p)
    // 非高亮节点退后:头像是不透明实心圆牌,不能用 opacity 压暗;改用"颜色降亮度"让其退后(材质 color 乘系数)
    const faceMat = (g.userData.face as THREE.Sprite).material as THREE.SpriteMaterial
    faceMat.color.setScalar(linked ? 1 : 0.25)
    ;(g.userData.label as THREE.Sprite).material.opacity = linked ? 1 : 0.12
  })
}

// 点亮一组人物(事件相关人物):只突出这些节点与其间连线,并让镜头框住所有人
function highlightPersons(ids: number[]) {
  highlightNodeIds.value = new Set(ids)
  applyHighlight()
  framePersons(ids)
}

// 镜头框选:把相机对准这些节点的中心,拉远到刚好能装下它们的最大距离(靠推进/拉远透视放大,而非撑大头像)
function framePersons(ids: number[]) {
  if (!built || !ids.length) return
  // 事件框选是"全局视角":退出之前聚焦的人,并让整张网回到原始布局(参与者位于 homePos)
  focusedId = null
  if (relayoutActive) startRelayout(null)

  // 以原始布局位置(homePos)算包围球:退焦重排复位后参与者正好落进框内
  const center = new THREE.Vector3()
  let n = 0
  for (const id of ids) {
    const g = nodeGroupMap[id]
    if (!g) continue
    center.add(g.userData.homePos as THREE.Vector3)
    n++
  }
  if (!n) return
  center.divideScalar(n)

  let r = 0
  for (const id of ids) {
    const g = nodeGroupMap[id]
    if (!g) continue
    r = Math.max(r, (g.userData.homePos as THREE.Vector3).distanceTo(center))
  }
  r = Math.max(r, 26) // 单个参与者也保持一定距离,别怼脸

  // 距离 = (包围球半径 + 余量) / sin(较小半视场角),保证所有人都落在画面内
  const vHalf = (camera.fov * Math.PI) / 360
  const hHalf = Math.atan(Math.tan(vHalf) * camera.aspect)
  const dist = (r + 18) / Math.sin(Math.min(vHalf, hHalf))
  startFocusAnim(orbitQ.clone(), center, dist)
}

// 聚焦过渡缓动:easeInOutCubic
function easeInOutCubic(x: number): number {
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2
}

function animate() {
  // 切到时间线(active=false)后暂停渲染循环,避免 WebGL 在后台空转拖慢切换、偶发卡住
  if (!props.active) {
    rafId = 0
    return
  }
  rafId = requestAnimationFrame(animate)
  const now = performance.now()
  const dt = Math.min(64, now - prevNow)
  prevNow = now
  const t = (now - t0) * 0.001

  if (focusAnim.active) {
    // 聚焦/退焦过渡:orbitQ slerp + 中心/缩放 lerp,easeInOutCubic 缓动
    focusAnim.t += dt / focusAnim.dur
    const k = Math.min(1, focusAnim.t)
    const e = easeInOutCubic(k)
    orbitQ.copy(focusAnim.fromQ).slerp(focusAnim.toQ, e)
    curFocus.copy(focusAnim.fromFocus).lerp(focusAnim.toFocus, e)
    camR = focusAnim.fromR + (focusAnim.toR - focusAnim.fromR) * e
    if (k >= 1) {
      focusAnim.active = false
      // 过渡结束才提交稳态逼近目标:此刻 curFocus/camR 已精确落在 toFocus/toR,无缝交接、无跳变
      focusTarget.copy(focusAnim.toFocus)
      targetCamR = focusAnim.toR
    }
  } else {
    // 自由/稳定态:滚轮缩放 + 聚焦中心指数逼近(自由视角在拖动松手/滚轮时手动记录,待机自转不会污染它)
    camR += (targetCamR - camR) * 0.12
    curFocus.lerp(focusTarget, 0.08)
  }
  const c = curFocus

  // 松手后惯性滑行(角速度四元数指数衰减);静止超过 IDLE_MS 后进入缓慢待机自转(过渡动画期间已清空 velQ)
  if (!down && !focusAnim.active) {
    orbitQ.premultiply(velQ)
    velQ.slerp(IDENT_Q, 0.06)
    if (now - lastInteract > IDLE_MS && velQ.angleTo(IDENT_Q) < 0.0004) {
      idleT += dt / 1000
      // 偏航:匀速慢转(90 秒一圈)
      orbitQ.premultiply(new THREE.Quaternion().setFromAxisAngle(Y_AXIS, AUTO_YAW_SPEED * (dt / 1000)))
      // 俯仰:绕相机当前右方向做小幅正弦起伏,增量由余弦给出,平滑无突变
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(orbitQ)
      const phase = idleT * (Math.PI * 2 / AUTO_PITCH_PERIOD)
      const pitch = AUTO_PITCH_AMP * (Math.PI * 2 / AUTO_PITCH_PERIOD) * Math.cos(phase) * (dt / 1000)
      orbitQ.premultiply(new THREE.Quaternion().setFromAxisAngle(right, pitch))
    } else {
      idleT = 0
    }
  }

  // 由轨道四元数作用在初始偏移 (0,0,camR) 上得到相机位置,并同步相机 up
  const offset = new THREE.Vector3(0, 0, camR).applyQuaternion(orbitQ)
  camera.position.copy(c).add(offset)
  camera.up.set(0, 1, 0).applyQuaternion(orbitQ)
  camera.lookAt(c)

  // 先更新人物节点的真实位置。优先驱动"聚焦重排"(整张网按关系距离分层);否则用旧的"拎起/原位"逻辑。
  if (relayoutActive) {
    relayoutT += dt / RELAY_DUR
    const k = Math.min(1, relayoutT)
    const e = easeInOutCubic(k)
    nodes.forEach((p) => {
      const g = nodeGroupMap[p.id]
      if (!g) return
      const from = relayoutFrom[p.id] || (g.userData.basePos as THREE.Vector3)
      const to = relayoutTo[p.id] || (g.userData.basePos as THREE.Vector3)
      g.position.copy(from).lerp(to, e)
    })
    if (k >= 1) {
      relayoutActive = false
      // 重排完成:把目标位置写回 basePos,使后续呼吸/淡影/复原都基于新位置。
      // 聚焦时写的是重排后位置;退焦时 relayoutTo 已是 homePos,自然把 basePos 复原。
      nodes.forEach((p) => {
        const g = nodeGroupMap[p.id]
        if (g && relayoutTo[p.id]) g.userData.basePos = relayoutTo[p.id].clone()
      })
    }
  } else {
    // 非重排期:节点位置以 basePos 为准(聚焦态下聚焦者已在重排后的最前位;自由态下全员在原布局位)
    nodes.forEach((p) => {
      const g = nodeGroupMap[p.id]
      if (!g) return
      g.position.copy(g.userData.basePos as THREE.Vector3)
    })
  }

  // 聚焦者的连线在线条排序里排前(便于看清),但**不给聚焦者头像强提 renderOrder**——
  // 否则拖动视角时聚焦者会被强行压到所有人前面,连"本来在 TA 前面的节点"也被压到后面,破坏三维空间逻辑。
  // 头像/标签/光环的水草交给 natural 排序,聚焦只负责"相机转过去看 TA",遮挡关系按真实三维来。
  edgeRecords.forEach((rec) => {
    const touch = focusedId != null && (rec.from === focusedId || rec.to === focusedId)
    rec.mesh.renderOrder = touch ? 1 : 0
    rec.label.renderOrder = touch ? 1 : 0
  })

  // 直线 + 一体化箭头:单一 billboard 几何逐帧面向相机;线端/箭头尖搭在目标圆圈视觉边缘
  // 端点跟随节点当前(可能被"拎起")的真实位置;顶点改为相对中点,让边按自身中点深度排序(而非全局原点)
  edgeRecords.forEach((rec) => {
    const camPos = camera.position
    const ga = nodeGroupMap[rec.from]
    const gb = nodeGroupMap[rec.to]
    if (!ga || !gb) return
    const a = ga.position
    const b = gb.position
    const dir = new THREE.Vector3().subVectors(b, a)
    if (dir.lengthSq() < 1e-8) return
    dir.normalize()

    // 端点偏移:沿"从 a 指向 b"的方向,把起点/终点各收到玻璃球表面(半径 R + 极小间隙,线贴住弹珠表面)
    const EDGE_GAP_WORLD = 1.5
    const rA = ((ga.userData.R as number) || NODE_R) + EDGE_GAP_WORLD
    const rB = ((gb.userData.R as number) || NODE_R) + EDGE_GAP_WORLD
    const start = new THREE.Vector3().copy(a).addScaledVector(dir, rA)   // 从源圆心向目标方向退到边缘
    const tip = new THREE.Vector3().copy(b).addScaledVector(dir, -rB)    // 从目标圆心向源方向退到边缘

    const segDir = new THREE.Vector3().subVectors(tip, start).normalize()
    const mid = new THREE.Vector3().addVectors(start, tip).multiplyScalar(0.5)
    // 宽度方向 = 指向镜头的方向 × 连线方向,垂直于连线且朝向相机 → 整条线/箭头是干净的正面二维条带
    const toCam = new THREE.Vector3().subVectors(camPos, mid).normalize()
    const side = new THREE.Vector3().crossVectors(segDir, toCam)
    if (side.lengthSq() < 1e-8) {
      side.set(1, 0, 0).cross(segDir)
      if (side.lengthSq() < 1e-8) side.set(0, 1, 0).cross(segDir)
    }
    side.normalize()

    // 关系标签与拾取盒都跟随边中点;拾取盒沿边方向拉伸
    rec.label.position.set(mid.x, mid.y + 5, mid.z)
    rec.pick.position.copy(mid)
    rec.pick.quaternion.setFromUnitVectors(Z_AXIS, dir)

    // 像素定宽:按边中点与相机的距离,把固定像素宽度换算成世界宽度(远近恒定,不随距离突变)
    const midDist = camPos.distanceTo(mid)
    const pxPerWorld = (2 * midDist * Math.tan((camera.fov * Math.PI) / 360)) / viewH
    const lineHalf = (LINE_PX / 2) * pxPerWorld
    const arrowHalf = ARROW_HALF_PX * pxPerWorld
    const arrowLen = ARROW_LEN_PX * pxPerWorld
    rec.pick.scale.set(EDGE_PICK_PX * pxPerWorld, EDGE_PICK_PX * pxPerWorld, a.distanceTo(b))

    // 顶点相对中点(排序原点移到中点;聚焦人物被真实"拎起"后即压过自己的连线)
    rec.mesh.position.copy(mid)
    const attr = rec.mesh.geometry.getAttribute('position') as THREE.BufferAttribute
    const s = new THREE.Vector3().subVectors(start, mid)
    const tp = new THREE.Vector3().subVectors(tip, mid)
    if (rec.directed) {
      const bs = new THREE.Vector3().copy(tip).addScaledVector(segDir, -arrowLen).sub(mid)
      attr.setXYZ(0, s.x + side.x * lineHalf, s.y + side.y * lineHalf, s.z + side.z * lineHalf)
      attr.setXYZ(1, s.x - side.x * lineHalf, s.y - side.y * lineHalf, s.z - side.z * lineHalf)
      attr.setXYZ(2, bs.x + side.x * arrowHalf, bs.y + side.y * arrowHalf, bs.z + side.z * arrowHalf)
      attr.setXYZ(3, bs.x - side.x * arrowHalf, bs.y - side.y * arrowHalf, bs.z - side.z * arrowHalf)
      attr.setXYZ(4, tp.x, tp.y, tp.z)
    } else {
      attr.setXYZ(0, s.x + side.x * lineHalf, s.y + side.y * lineHalf, s.z + side.z * lineHalf)
      attr.setXYZ(1, s.x - side.x * lineHalf, s.y - side.y * lineHalf, s.z - side.z * lineHalf)
      attr.setXYZ(2, tp.x - side.x * lineHalf, tp.y - side.y * lineHalf, tp.z - side.z * lineHalf)
      attr.setXYZ(3, tp.x + side.x * lineHalf, tp.y + side.y * lineHalf, tp.z + side.z * lineHalf)
    }
    attr.needsUpdate = true
  })

  // 头像呼吸 + 悬停点亮(聚焦靠相机推进透视放大,头像本身尺寸恒定、不缩放)
  nodes.forEach((p) => {
    const g = nodeGroupMap[p.id]
    if (!g) return
    const phase = (p.id * 1.7) % (Math.PI * 2)
    const breath = Math.sin(t * 1.4 + phase)

    // 悬停放大:三维球 + 朝前照片面一起缩放(整组缩放即可)。事件相关人物的"放大"交给镜头框选,不硬撑头像本身。
    const hover = p.id === hoveredId ? 1.14 : 1
    g.scale.setScalar(hover)
    // 聚焦圈(人物色圆环,呼吸常亮) 与 悬停圈(白色) 复用同一个 ring,聚焦优先于悬停
    const ring = g.userData.ring as THREE.Sprite
    const ringMat = ring.material as THREE.SpriteMaterial
    if (p.id === focusedId) {
      ringMat.color.set(p.color || dynastyColor(p.dynasty))
      ringMat.opacity = 0.55 + 0.3 * Math.sin(t * 2.2 + phase)
    } else if (p.id === hoveredId) {
      ringMat.color.set('#ffffff')
      ringMat.opacity = 0.9
    } else {
      ringMat.opacity = 0
    }

    // 聚焦人物不再强提任何 Sprite 的渲染层级:保持自然深度排序,拖动视角时"谁在前谁挡谁"按真实三维来。

    // 光晕:高亮者才点亮(朝代/事件组全员;聚焦只点聚焦者本人)。群体高亮 2.0x,单独聚焦 1.6x。
    // 光晕始终垫在头像后面(背光):沿视线方向往后推,让不透明头像挡住光晕中心,只露外圈。
    const halo = g.userData.halo as THREE.Sprite
    const haloLit = nodeHalo(p)
    const boost = (highlightNodeIds.value.size || props.dynastyFilter.length) ? 1.8 : 1.6
    halo.material.opacity = haloLit ? T.haloBase * boost + breath * 0.02 : 0
    halo.scale.setScalar(g.userData.haloBase * boost * (1 + breath * 0.03))
    const hCam = new THREE.Vector3().subVectors(camera.position, g.position).normalize()
    halo.position.copy(hCam).multiplyScalar(-6)

    // 名字标签:基准点在"圆圈上方",再整体沿"指向镜头"方向往外推出头像半径多一点,
    // 使其浮在自己头像前方的安全深度——不被自己的实心头像挡住,但仍会被真正更近的其它对象挡住。
    const lab = g.userData.label as THREE.Sprite
    if (lab) {
      const R = (g.userData.R as number) || 11
      const toCam = new THREE.Vector3().subVectors(camera.position, g.position).normalize()
      lab.position.set(toCam.x * (R + 2), R + 5, toCam.z * (R + 2))
    }
  })

  renderer.render(scene, camera)
}

function onResize() {
  if (!built || !renderer || !wrapEl.value) return
  const w = wrapEl.value.clientWidth
  const h = wrapEl.value.clientHeight
  if (!w || !h) return
  viewH = h
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

function ensureBuilt() {
  if (built) return
  if (!props.active || props.nodes.length === 0) return
  buildGraph()
}

// 数据变化(新增人物/关系)后整体重建,并保留视角参数避免跳动
function teardown() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  if (wrapEl.value) {
    wrapEl.value.removeEventListener('mousedown', onMouseDown)
    wrapEl.value.removeEventListener('wheel', onWheel)
  }
  if (renderer) {
    renderer.domElement.removeEventListener('click', onClick)
  }
  pickMeshes = []
  edgePickMeshes = []
  nodeGroupMap = {}
  edgeRecords = []
  dimmedEdges.value = new Set()
  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
  }
  built = false
  builtReactive.value = false
}

function rebuild() {
  if (!wrapEl.value) return
  teardown()
  buildGraph()
}

onMounted(() => {
  nextTick(ensureBuilt)
  window.addEventListener('resize', onResize)
})

watch(
  () => ({ n: props.nodes, e: props.edges }),
  () => {
    if (!built) nextTick(ensureBuilt)
    else rebuild()
  },
)

watch(
  () => props.active,
  (a) => {
    if (!a) {
      // 离开关系网:定格当前机位,供下次进入恢复
      saveCamera()
      return
    }
    nextTick(() => {
      ensureBuilt()
      onResize()
      // 重新激活:重置时间基准后续上渲染循环,避免切回来瞬间镜头跳变 / 立刻触发待机自转
      prevNow = performance.now()
      lastInteract = performance.now()
      if (built && !rafId) rafId = requestAnimationFrame(animate)
      // 每次进入都播放运镜:飞回上次定格机位(首次进入时 saved 即初始机位)
      hasEntered = true
      playEntryDolly(savedOrbitQ, savedFocus, savedCamR, 1200)
    })
  },
)

watch(
  () => props.highlightId,
  (pid) => {
    currentHighlightId = pid ?? null
    dimmedEdges.value = new Set() // 切换聚焦人物:清空熄灭集合,其关系默认全亮
    highlightNodeIds.value = new Set() // 事件人物点亮让位于人物聚焦
    applyHighlight()
  },
)

watch(
  () => props.dynastyFilter,
  (filter) => {
    highlightNodeIds.value = new Set() // 切到朝代筛选:退出事件人物点亮
    applyHighlight()
    // 选择朝代后,把镜头框住这些朝代的全体人物(与搜索选事件的框选一致);清除筛选时不框选
    if (filter.length) {
      const ids = nodes.filter((p) => filter.includes(dynastyColor(p.dynasty))).map((p) => p.id)
      framePersons(ids)
    }
  },
)

// 朝代"点亮/熄灭"变化:重新计算人物/连线显隐(无需重建,仅切换 visible)
watch(
  () => props.unlitDynasties,
  () => applyHighlight(),
)
watch(dimmedEdges, (s) => {
  applyHighlight()
  emit('edge-dim-change', [...s])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  teardown()
})

defineExpose({ focusPerson, toggleEdgeHighlight, highlightPersons })
</script>

<template>
  <div id="graphWrap" ref="wrapEl">
    <div v-if="!builtReactive" class="graph-fallback">3D 引擎加载中…</div>
  </div>
</template>

<style scoped>
.graph-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
}
</style>
