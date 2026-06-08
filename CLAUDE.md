# DarkFindV5

读取游戏原始 JSON 数据 → Python 清洗 → 输出后端 JSON 数据文件 → Ant Design React SSG (Vite) → 静态部署 → 浏览器端注水渲染。

> **参考项目**：文中所提「原项目」「v4」「findItemV4」均指 `/home/mio/fmod/findItemV4/`。

## 项目结构

```
DarkFindV5/
├── api/                  # Python 数据处理管道
│   ├── main.py               # 入口：读取 data/ 原始 JSON，清洗后输出到 output/
│   ├── config.py             # 路径配置
│   ├── data/                 # 原始 JSON 输入（.gitignore 忽略？根据需求）
│   └── output/               # 清洗后的 JSON 输出（供前端消费）
├── web/                 # React 前端（SSG）
│   ├── src/
│   │   ├── main.tsx          # 入口：注水渲染
│   │   ├── App.tsx           # Ant Design 暗色主题 + zhCN 配置
│   │   ├── pages/            # 页面组件
│   │   ├── components/       # 通用组件
│   │   ├── hooks/            # 自定义 hooks
│   │   └── types/            # TypeScript 类型定义
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── .github/workflows/        # GitHub Actions CI/CD
└── .gitignore
```

## 开发流程

### 迭代工作流

```
[阶段修改前]  git commit -m "WIP: <描述>"   # 本地提交当前进度
       ↓
[修改代码]   编辑 api/ 或 web/ 代码
       ↓
[准备验证]   停止修改，执行构建部署
       ↓
[验证页面]   打开浏览器预览
       ↓
[循环]       继续修改或完成
```

### 构建部署（本地验证）

```bash
# 1. 提交当前进度（修改前 / 阶段性完成时）
git commit -am "WIP: <描述>"

# 2. 运行数据管道（清洗 JSON → 输出到 api/data/）
cd api && python main.py

# 3. 复制数据到前端静态目录
rm -rf ../web/public/data && cp -r data ../web/public/data

# 4. 前端类型检查 + 生产构建
cd ../web && npm run build

# 5. 预览构建产物（打开 http://localhost:4173）
npm run preview
```

### 开发服务器（实时修改）

```bash
# 后端数据管道
cd api && python main.py         # 每次数据变更后运行

# 前端开发服务器（热更新）
cd web && npm run dev

# 预览生产构建
cd web && npm run preview
```

### 注意

- `python main.py` 必须在前端 `npm run build` 之前运行，否则前端数据是旧的
- TypeScript 类型检查在 `npm run build` 中自动执行，也可手动：`npx tsc --noEmit`
- 构建产物在 `web/dist/`，用 `npm run preview` 本地预览

## CI/CD（GitHub Actions）

工作流 `.github/workflows/deploy.yml`：

| 事件 | 操作 |
|------|------|
| push `main` | `npm ci` → `tsc --noEmit` → `vite build` → push to `gh-pages` branch |
| PR `main` | `npm ci` → `tsc --noEmit` → `vite build`（不部署） |

**部署前提**：在 GitHub 仓库 Settings → Pages → Source 选择 "Deploy from a branch" → `gh-pages` branch → `/ (root)`。

## 布局说明

页面分为三级，每级栅格列数不同：

| 级别 | 页面 | 一行列数 | 组件 |
|------|------|---------|------|
| 主页 | `index` | 4 | Card 导航卡片（1x1 等宽） |
| 子页列表 | `items`, `monsters`, `props` | 3 | Card 列表项（1x1 等宽） |
| 最终页 | 单个实体详情页 | 4 | 地图卡片（兼容 1x1 / 2x1 / 1x2 / 2x2） |

### 主页（index）— 一行 4 列

```
┌────┐┌────┐┌────┐┌────┐
│物品 ││怪物 ││实体 ││模块 │
└────┘└────┘└────┘└────┘  ← Row gutter=16, Col span=6 (24/4)
```

- 使用 `<Row gutter={16}>` + `<Col span={6}>`
- 每个卡片内 `Statistic` 显示数量

### 子页列表 — 一行 3 列

```
┌──────┐┌──────┐┌──────┐
│ 物品1 ││ 物品2 ││ 物品3 │
└──────┘└──────┘└──────┘
│ 物品4 ││ 物品5 ││ 物品6 │
└──────┘└──────┘└──────┘  ← Col span=8 (24/3)
```

- `<Col xs={24} sm={12} md={8}>`（小屏 1 列，中屏 2 列，大屏 3 列）
- 卡片点击跳转到最终页

### 最终页（详情页）— 一行 4 列，兼容异形模块

```
┌──┐┌──┐┌──┐┌──┐
│1x1││1x1││1x1││1x1│
└──┘└──┘└──┘└──┘

异形模块用 grid-column span 处理：
┌──────┐┌──┐┌──┐
│ 2x1  ││1x1││1x1│  ← 2x1 span 2 列
└──────┘└──┘└──┘
┌──────┐┌──┐┌──┐   ← 下一行
│ 2x2  ││1x1││1x1│
│      │└──┘└──┘
└──────┘          ← 2x2 span 2 列 + 2 行
┌──┐┌──────┐
│1x1││ 1x2  │        ← 1x2 竖排
└──┘└──────┘
```

- 基础栅格 `<Col span={6}>`（一行 4 列）
- 地图卡片容器用 CSS Grid 布局：
  - `size_x >= 2`→ `grid-column: span 2`（宽度占 2 列）
  - `size_y >= 2`→ 通过 `grid-row: span 2` 或内部 stretch（高度自适应）
  - 容器 `aspect-ratio: {size_x} / {size_y}` 保持比例
- 地图卡片排序：按 `size_y, size_x` 升序，即 1x1 → 2x1 → 1x2 → 2x2
- 坐标范围：`range = max(size_x, size_y) * 1600`（默认 1600 单位/格）

## 数据流

```
游戏原始 JSON（Output/Exports/DungeonCrawler/...）
    ↓ Python: api/main.py (清洗/转换 + SQLite + FTS5)
后端 JSON（api/data/ → 复制到 web/public/data/）
    ↓ Vite build 打包到 web/dist/data/
    ↓ GitHub Actions 部署到 gh-pages
    ↓ 浏览器 fetch("./data/index.json") → 注水渲染
```
