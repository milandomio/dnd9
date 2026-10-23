# 快速开始

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.10+（仅标准库，无需 pip install） |
| Node.js | 20+ |
| npm | 随 Node 提供 |

### 一键构建

```bash
git clone https://github.com/milandomio/dnd9.git
cd dnd9
./deploy.sh
```

脚本会依次：检查环境 → 从预置数据库导出 JSON → 安装前端依赖 → 构建静态站点 → 在 8081 端口启动预览。

访问 <http://localhost:8081/>。

### 常用参数

```bash
./deploy.sh --port 9000     # 指定预览端口
./deploy.sh --build-only    # 只构建，产物在 web/dist
./deploy.sh --help          # 查看说明
```

## 不依赖游戏文件也能部署

这是本项目的关键设计：**普通用户不需要拥有游戏或解包工具**。

仓库内提交了 `api/data/darkfindv5.db`（约 47 MB），它是从游戏资产完整导出的 SQLite 数据库，包含全部实体、掉落、坐标与翻译。

数据管道的入口会先判断数据源是否可用：

```
数据源完整  → REBUILD_REQUIRED  重新解析游戏资产、重建 DB
数据源缺失  → DB_ONLY          直接用仓库里的 DB 导出 JSON
两者都缺    → FAIL_FAST        报错退出
```

判断逻辑位于 `api/src/db_freshness.py`。普通用户的环境里没有 `Output/Exports/` 目录，因此自动走 **DB_ONLY**，跳过所有游戏资产解析，只做「DB → JSON → 静态页面」这一段，几十秒即可完成。

### 部署到静态托管

```bash
./deploy.sh --build-only
# 将 web/dist 整个目录上传到托管服务
```

`web/dist` 是纯静态资源，不需要 Node 或 Python 运行时。项目自带 `_redirects`（Cloudflare Pages）与 `404.html`，多语言路由可直接工作。

## 项目结构

```
.
├── api/                    数据管道（Python）
│   ├── main.py             管道入口
│   ├── data/darkfindv5.db  预生成数据库（普通用户的数据源）
│   └── src/
│       ├── db/             schema、importers、repositories
│       ├── *_builder.py    各页面的数据组装
│       └── config.py       路径与常量
├── web/                    前端（React + Vite + Ant Design）
│   ├── scripts/ssg.mjs     静态站点生成
│   └── src/pages/          14 个页面
├── docs/                   设计文档与变更记录
└── deploy.sh               一键构建脚本
```

## 页面

| 路径 | 内容 |
|------|------|
| `/:lang` | 首页 |
| `/:lang/items/:name` | 物品详情 + 掉落来源 + 地图分布 |
| `/:lang/monsters/:name` | 怪物详情 + 掉落表 |
| `/:lang/lootdrops/:name` | 掉落详情 + 按地图分组的爆率 |
| `/:lang/props/:name` | 实体详情 |
| `/:lang/dungeon_modules/:group/:name` | 地图模块布局与实体坐标 |
| `/:lang/crafts/:merchant` | 工匠配方（含药水属性） |
| `/:lang/dungeon_shops/:region` | 地牢商店库存与价格 |
| `/:lang/quest_items` `/:lang/quest_npc` | NPC 任务与任务物品 |

## 技术栈

**后端**：Python 标准库（无第三方依赖）、SQLite

**前端**：React 18、TypeScript、Vite、Ant Design、react-helmet-async、vite-plugin-pwa

**部署**：SSG 预渲染 + GitHub Actions → Cloudflare Pages / GitHub Pages

## 开发

开发模式（跳过 SSG，启用 HMR）：

```bash
cd web && npm run dev -- --port 8090
```

质量检查：

```bash
cd api && ./lint.sh                     # ruff + black
cd web && npm run check                 # eslint + prettier + tsc
cd api && python3 -m unittest discover -s tests
```

需要重新解析游戏资产时（仅项目维护者）：

```bash
cd api && python3 main.py --rebuild-db
```

## 文档

| 文档 | 内容 |
|------|------|
| [docs/BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) | 构建、启动、部署流程 |
| [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) | 开发与提交规范 |
| [docs/AGENT_REFERENCE.md](docs/AGENT_REFERENCE.md) | 项目结构与组件职责 |
| [docs/REFERENCE_DATA_PIPELINE.md](docs/REFERENCE_DATA_PIPELINE.md) | 数据管道细节 |
| [docs/REFERENCE_MAP_MODULES.md](docs/REFERENCE_MAP_MODULES.md) | 地图模块收录规则 |
| [docs/SESSION_CHANGES.md](docs/SESSION_CHANGES.md) | 变更记录 |

## 许可

[MIT](LICENSE)
