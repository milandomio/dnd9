# PWA 成熟化路线图

> 实施日期：2026-07-14
> 目标：将项目从"基础 PWA 骨架"升级为"成熟可安装 PWA"

## 当前状态

已有 `vite-plugin-pwa` + Workbox，完成：
- Service Worker 自动注册（`registerSW.js`）
- Workbox runtime 缓存（NetworkFirst / StaleWhileRevalidate）
- 基础 manifest（name / short_name / start_url / icons）
- SWUpdateBanner 离线就绪提示

## 6 项改造

### 1. Manifest 完善

| 字段 | 现状 | 目标 |
|------|------|------|
| `description` | ❌ 缺失 | `"Dark and Darker 游戏数据导航工具"` |
| `lang` | ⚠️ 生成值为 `"en"` | `"zh-Hans"` |
| `categories` | ❌ 缺失 | `["games", "utilities"]` |
| `orientation` | ❌ 缺失 | `"any"` |
| icons `purpose` | ❌ 缺失 | 追加 `"any maskable"` |

**涉及文件：** `vite.config.ts`

### 2. iOS 主屏幕支持

在 `<head>` 中添加：
- `<meta name="apple-mobile-web-app-capable" content="yes">`
- `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
- `<link rel="apple-touch-icon" href="/icons/icon-192.png">`

**涉及文件：** `index.html`

### 3. Meta 补充

- `<meta name="theme-color" content="#141414">` — 地址栏颜色
- `<meta name="description" content="...">` — SEO 描述

**涉及文件：** `index.html`

### 4. 离线回退页面

- 创建 `public/offline.html` — 简洁的离线提示页（暗色主题），加入 precache
- 客户端 `OfflineDetector` 组件 — 监听 `online`/`offline` 事件，显示离线横幅

**涉及文件：** `public/offline.html`（新建）、`src/components/OfflineDetector.tsx`（新建）

### 5. 更新通知机制

重写 `SWUpdateBanner.tsx`：
- 使用 `workbox-window` 监听 `installed` 事件
- 首次安装 → "离线模式已就绪"
- 版本更新 → "新版本已下载，点击刷新以应用" + 刷新按钮

**涉及文件：** `src/components/SWUpdateBanner.tsx`

### 6. 安装提示

新建 `InstallPrompt` 组件：
- 捕获 `beforeinstallprompt` 事件
- 延迟到用户交互后触发 `prompt()`
- 监听 `appinstalled` 事件，安装后隐藏提示

**涉及文件：** `src/components/InstallPrompt.tsx`（新建）

## 不做的事

| 特性 | 原因 |
|------|------|
| `navigateFallback`（SW 级） | 会与 SSG NetworkFirst 缓存冲突，详见 `docs/PWA_SW_PLAN.md` |
| Background Sync | 当前无离线提交需求 |
| Push Notification | 无需推送 |
| Periodic Sync | 数据更新由用户主动刷新触发 |
