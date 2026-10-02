# 人物志 (Chronicle)

一个**本地优先**的历史人物关系与事件记录应用。用来在听历史内容时随手记录人物、事件与人物关系,并在一条时间线和一张立体关系网中浏览。

- 后端:FastAPI + SQLAlchemy + SQLite,数据存本地
- 前端:Nuxt 3 + TypeScript + Three.js(3D 关系网)
- 桌面端:Electron 外壳 + PyInstaller 打包的独立后端,双击即用,无需装 Python / Node

---

## 目录结构

```
project-root/
├── .gitignore
├── README.md
├── backend/                     # FastAPI 后端
│   ├── requirements.txt         # 锁定版本
│   ├── run.py                   # PyInstaller 打包入口(与 app/main.py 并列)
│   ├── local_data/              # 运行时数据
│   │   ├── sqlite/              #   chronicle.db(自动生成,不入库)
│   │   ├── avatars/             #   默认头像库(按人物名命名,如 关羽.jpg)
│   │   └── icons/               #   App 图标(当前用 星图_朱砂.png,打包时自动转 .icns)
│   └── app/
│       ├── main.py              # 入口:挂路由、CORS、自动建表 + 轻量迁移、托管前端静态文件(打包模式)
│       ├── core/config.py       # DB 路径、端口;区分开发/打包两种模式
│       ├── db/                  # engine / session / base
│       ├── models/              # person / event / event_person / relation / custom_dynasty
│       ├── schemas/             # Pydantic
│       ├── crud/                # 增删改查(删除人物时级联清理关系、空事件)
│       ├── services/            # 序列化 / 默认头像库
│       └── api/v1/endpoints/    # persons / events / relations / graph / custom_dynasties / avatars
├── fronted_Nuxt/                # Nuxt 3 前端
│   ├── package.json
│   ├── nuxt.config.ts           # dev proxy:/api -> 后端
│   ├── app.vue
│   ├── assets/css/main.css      # 全局样式
│   ├── composables/             # useBackendApi / usePersons / useEvents / useRelations / useDynasties / useAvatars / useToast
│   ├── components/              # GraphView / TimelineView / PersonDrawer / EventPopover / SideRail / SearchBar / AddPanel / AppSelect / AppMultiSelect 等
│   ├── pages/index.vue          # 单页:内部切换 graph / timeline 两个视图
│   ├── types/chronicle.ts       # 数据形状
│   └── utils/dynasty.ts         # 朝代配色 / 年份格式化
├── desktop/                     # Electron 桌面端外壳
│   ├── main.js                  # 主进程:找端口、拉后端、开窗口、退出清理
│   ├── package.json             # electron + electron-builder 配置(含 extraResources / mac 目标)
│   ├── build/                   # PyInstaller 产物(中间产物,不入库)
│   └── dist/                    # 最终 .app / .dmg / .zip(不入库)
└── scripts/
    └── build-app.sh             # 一键打包脚本
```

---

## 使用方式

### 方式 A:桌面 App(推荐,无需任何环境)

1. 从 GitHub Releases 下载 `人物志-*.dmg`,双击挂载,把 `人物志.app` 拖进「应用程序」。
2. 点击图标直接打开,和普通 macOS 软件一样。

> **两点说明**
> - **未签名**:App 未做 Apple 公证,别人从网上下载后首次打开会提示「无法验证开发者」,需**右键 App → 打开 → 再点打开**(每台电脑一次)。
> - **仅 Apple Silicon**:当前只打 arm64 包,支持 M1/M2/M3/M4;Intel Mac 需另行构建 x64 版。

数据保存在 `~/Library/Application Support/chronicle-desktop/sqlite/chronicle.db`,**与源码目录无关**,升级、重装 App 都不丢数据。

### 方式 B:源码运行(开发)

见下文「一、启动后端」「二、启动前端」。

---

## 一、启动后端(隔离虚拟环境)

后端依赖**完全隔离**在 `backend/.venv` 中,绝不装进系统 Python。

首次运行先创建虚拟环境并安装依赖:

```bash
cd backend
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

(没有 `uv` 时可用 `python3 -m venv .venv` + `.venv/bin/pip install -r requirements.txt`。)

之后每次启动:

```bash
cd backend
.venv/bin/python app/main.py
```

启动后监听 `http://127.0.0.1:8000`(API 文档在 `/docs`),首次启动自动建表,数据库为空,由前端「添加」面板或 API 写入内容。

> **端口被占用?** 若 8000 已被占用,可指定端口:
>
> ```bash
> CHRONICLE_PORT=8001 .venv/bin/python app/main.py
> ```
>
> 前端代理也要指向它(见下)。Windows 下用 `.venv\Scripts\python app\main.py`。

## 二、启动前端(Nuxt 3)

```bash
cd fronted_Nuxt
npm install
npm run dev      # http://localhost:3000
```

前端通过 `useBackendApi` 统一请求,`nuxt.config.ts` 里配置了 dev proxy,把 `/api/**` 转发到后端(默认 `http://127.0.0.1:8000`)。

**后端不在 8000 端口时**,启动前端时指定后端源地址:

```bash
CHRONICLE_BACKEND_ORIGIN=http://127.0.0.1:8001 npm run dev
```

(也可改走直连:`NUXT_PUBLIC_API_BASE=http://127.0.0.1:8001/api npm run dev`,后端已开 CORS 允许 `localhost:3000`。)

---

## 三、打包桌面 App

一键脚本完成「前端静态构建 → 后端 PyInstaller 打包 → Electron 打包」三步:

```bash
./scripts/build-app.sh
```

产物在 `desktop/dist/`:

- `mac-arm64/人物志.app` — 直接可用的 App
- `人物志-*.dmg` — 分发用安装镜像
- `人物志-*-mac.zip` — 免安装压缩包

> **环境完全隔离**:后端由 PyInstaller 打包为独立可执行文件(含 Python 运行时),前端打包为静态文件塞进后端;Electron / electron-builder 装在 `desktop/node_modules`(本地)。全程不写系统 Python、不做全局 npm 安装。

### 发布到 GitHub

把 `人物志-*.dmg` 上传到 **GitHub Releases**(仓库 → Releases → Create a new release → 拖入 dmg),不要直接 commit 进 git 仓库(有 100MB 单文件限制,也会撑大历史)。Release 支持单文件最大 2GB。

> 想让别人「双击即开、零提示」,需用 Apple Developer ID($99/年)签名 + 公证;不签名的话,别人右键「打开」一次即可。

---

## 四、界面操作

- 默认进入**关系网**(深色 3D 宇宙):拖动旋转、滚轮缩放、悬停高亮、点击节点打开右侧人物抽屉并高亮其一度关系;左上角为朝代颜色图例。
- 左侧竖向切换栏(🕸 关系网 / ⟶ 时间线)切换视图;时间线为浅色横向滚轴,事件卡片上下交错,右下角 ◍ 查看朝代色卡。
- 右下角「+」打开添加面板,录入人物 / 关系 / 事件。
- 右上角搜索框搜人物/事件(`⌘K` / `Ctrl+K` 聚焦)。
- `Esc` 关闭抽屉 / 浮卡。

---

## 五、后端 API

前缀 `/api/v1`,返回 JSON(年份用整数,负数 = 公元前):

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/persons` | 人物列表 / 新建 |
| GET/PUT/DELETE | `/persons/{id}` | 单个人物 |
| GET | `/persons/{id}/detail` | 人物 + 其全部事件 + 其全部关系(供抽屉) |
| GET/POST | `/events` | 事件列表 / 新建 |
| GET/PUT/DELETE | `/events/{id}` | 单个事件 |
| GET | `/events/timeline?from=&to=` | 时间线数据(按 `year_start` 排序) |
| GET/POST | `/relations` | 关系列表 / 新建 |
| DELETE | `/relations/{id}` | 删除关系 |
| GET | `/graph` | 关系网数据 `{nodes, edges}` |
| GET/POST | `/custom-dynasties` | 自定义朝代/国家列表 / 新建 |
| PUT/DELETE | `/custom-dynasties/{id}` | 编辑 / 删除自定义朝代 |
| GET | `/avatars` | 默认头像库列表 |
| GET | `/avatars/file/{name}` | 按人物名取默认头像图片 |

## 六、数据模型(SQLite)

| 表 | 字段 |
|---|---|
| `persons` | id, name, dynasty, secondary_dynasties(JSON), birth_year, death_year, summary, identity, color, avatar |
| `events` | id, title, description, year_start, year_end, dynasty, location |
| `event_persons` | id, event_id, person_id, role(如"主将/主谋/被害") |
| `relations` | id, from_person_id, to_person_id, label, directed(是否单向) |
| `custom_dynasties` | id, name, color |

## 七、朝代配色(全局视觉主干)

```
春秋 #7d7aff · 战国 #0a84ff · 秦 #30d158 · 汉 #ff9f0a · 赵 #d4b800 · 燕 #ff6482 · 默认 #8e8e93
```
