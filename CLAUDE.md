# DarkFindV5

读取游戏原始 JSON 数据 → Python 清洗 → 输出后端 JSON 数据文件 → Ant Design React SSG (Vite) → 静态部署 → 浏览器端注水渲染。

## 项目结构

```
DarkFindV5/
├── backend/                  # Python 数据处理管道
│   ├── main.py               # 入口：读取 data/ 原始 JSON，清洗后输出到 output/
│   ├── config.py             # 路径配置
│   ├── data/                 # 原始 JSON 输入（.gitignore 忽略？根据需求）
│   └── output/               # 清洗后的 JSON 输出（供前端消费）
├── frontend/                 # React 前端（SSG）
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

```bash
# 1. 后端：读取原始 JSON → 清洗 → 输出
cd backend && python main.py

# 2. 前端：安装依赖、开发、构建
cd frontend
npm install        # 首次
npm run dev        # 开发服务器
npm run build      # SSG 生产构建（输出到 dist/）

# 3. 预览构建产物
npm run preview
```

## CI/CD（GitHub Actions）

工作流 `.github/workflows/deploy.yml`：

| 事件 | 操作 |
|------|------|
| push `main` | `npm ci` → `tsc --noEmit` → `vite build` → push to `gh-pages` branch |
| PR `main` | `npm ci` → `tsc --noEmit` → `vite build`（不部署） |

**部署前提**：在 GitHub 仓库 Settings → Pages → Source 选择 "Deploy from a branch" → `gh-pages` branch → `/ (root)`。

## 数据流

```
原始 JSON (backend/data/)
    ↓ Python: main.py (清洗/转换)
后端 JSON (backend/output/data.json → 前端静态资源)
    ↓ Vite build 复制到 dist/
    ↓ GitHub Actions 部署到 Pages
    ↓ 浏览器 fetch("./data.json") → 注水渲染
```
