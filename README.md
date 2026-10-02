# 人物志 (Chronicle)

一个**本地优先**的历史人物关系与事件记录应用。用来在听历史内容时随手记录人物、事件与人物关系,并在一条时间线和一张立体关系网中浏览。

- 后端:FastAPI + SQLAlchemy + SQLite,数据存本地 `backend/local_data/sqlite/chronicle.db`
- 前端:Nuxt 3 + TypeScript + Three.js(3D 关系网)

---

## 目录结构

```
project-root/
├── .gitignore
├── README.md
├── backend/                     # FastAPI 后端
│   ├── requirements.txt         # 锁定版本
│   ├── local_data/              # 运行时数据(不入库)
│   │   ├── sqlite/              #   chronicle.db(自动生成)
│   │   └── avatars/             #   默认头像库(按人物名命名,如 关羽.jpg)
│   └── app/
│       ├── main.py              # 入口:挂路由、CORS、自动建表 + 轻量迁移
│       ├── core/config.py       # DB 路径、端口
│       ├── db/                  # engine / session / base
│       ├── models/              # person / event / event_person / relation / custom_dynasty
│       ├── schemas/             # Pydantic
│       ├── crud/                # 增删改查
│       ├── services/            # 序列化 / 默认头像库
│       └── api/v1/endpoints/    # persons / events / relations / graph / custom_dynasties / avatars
└── fronted_Nuxt/                # Nuxt 3 前端
    ├── package.json
    ├── nuxt.config.ts           # dev proxy:/api -> 后端
    ├── app.vue
    ├── assets/css/main.css      # 全局样式
    ├── composables/             # useBackendApi / usePersons / useEvents / useRelations / useDynasties / useAvatars / useToast
    ├── components/              # GraphView / TimelineView / PersonDrawer / EventPopover / SideRail / SearchBar / AddPanel / DynastySelect 及表单与浮层组件
    ├── pages/index.vue          # 单页:内部切换 graph / timeline 两个视图
    ├── types/chronicle.ts       # 数据形状
    └── utils/dynasty.ts         # 朝代配色 / 年份格式化
```

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

(也可先 `source .venv/bin/activate`,再 `cd backend/app && python main.py`。)

启动后监听 `http://127.0.0.1:8000`(API 文档在 `/docs`),首次启动自动建表,数据库为空,由前端「添加」面板或 API 写入内容。

> **端口被占用?** 若 8000 已被其它服务占用(例如本机的 DMS 项目),可这样指定端口:
>
> ```bash
> CHRONICLE_PORT=8001 .venv/bin/python app/main.py
> ```
>
> 记住这个端口,前端代理也要指向它(见下)。
>
> Windows 下用 `.venv\Scripts\python app\main.py`。

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

生产构建:

```bash
npm run build
npm run start     # node .output/server/index.mjs
```

---

## 三、使用

打开 `http://localhost:3000`:

- 默认进入**关系网**(深色 3D 宇宙):拖动旋转视角、滚轮缩放、悬停高亮节点、点击节点打开右侧人物抽屉并高亮其一度关系;左上角为朝代颜色图例。
- 左侧竖向玻璃切换栏(🕸 关系网 / ⟶ 时间线)切换两个视图;时间线为浅色横向滚轴,事件卡片上下交错,点击浮起事件详情,右下角 ◍ 查看朝代色卡。
- 右下角「+」按钮打开添加面板,录入人物 / 关系 / 事件。
- 右上角搜索框搜人物/事件(`⌘K` / `Ctrl+K` 聚焦,回车或点击结果跳转)。
- `Esc` 关闭抽屉 / 浮卡。

## 四、后端 API

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

## 五、数据模型(SQLite)

| 表 | 字段 |
|---|---|
| `persons` | id, name, dynasty, secondary_dynasties(JSON), birth_year, death_year, summary, identity, color, avatar |
| `events` | id, title, description, year_start, year_end, dynasty, location |
| `event_persons` | id, event_id, person_id, role(如"主将/主谋/被害") |
| `relations` | id, from_person_id, to_person_id, label, directed(是否单向) |
| `custom_dynasties` | id, name, color |

## 六、朝代配色(全局视觉主干)

```
春秋 #7d7aff · 战国 #0a84ff · 秦 #30d158 · 汉 #ff9f0a · 赵 #d4b800 · 燕 #ff6482 · 默认 #8e8e93
```
