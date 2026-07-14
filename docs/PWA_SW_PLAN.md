# Service Worker 集成记录

## 状态：已完成 (2026-07-14)

为静态网站添加了离线缓存和运行时网络策略，同时修复了缓存机制中的若干问题（详见 `CACHE_FIXES.md`）。

> **缓存策略**: SW 运行时缓存无时间过期；SSG 路由由 NetworkFirst 访问后缓存（含 SSR 数据）；`navigateFallback` 未启用（否则会覆盖 SSG 路由缓存）；`registerSW.js` 已预缓存保障离线注册。

## 实施步骤

### 1. 安装依赖

```bash
cd web && npm install vite-plugin-pwa
```

`vite-plugin-pwa` 已安装，作用：
- 构建时自动生成 Service Worker 脚本（基于 Workbox）
- 通过 Vite HTML transform 注入注册代码到 index.html
- 生成 `manifest.json`

### 2. vite.config.ts 配置

在 client build plugin 列表中已添加 `VitePWA` 插件：

```ts
VitePWA({
  registerType: 'autoUpdate',
  workbox: {
    // navigateFallback 未启用：SSG 路由 HTML（含 SSR 数据）由 NetworkFirst 访问后缓存，
    // 离线重复访问正常显示。预缓存 registerSW.js 确保 SW 注册脚本离线可用。
    navigateFallback: undefined,
    globPatterns: ['assets/**/*.{js,css}', 'registerSW.js'],
    runtimeCaching: [
      {
        // SSG HTML 页面：NetworkFirst，访问后缓存，离线重复访问正常显示
        urlPattern: ({ request }) => request.mode === 'navigate',
        handler: 'NetworkFirst',
        options: { cacheName: 'df5-html', expiration: { maxEntries: 1300 } },
      },
      {
        // meta.json：5 分钟 TTL
        urlPattern: /\/meta\.json$/,
        handler: 'StaleWhileRevalidate',
        options: { cacheName: 'df5-meta', expiration: { maxEntries: 1, maxAgeSeconds: 300 } },
      },
      {
        urlPattern: /^\/data\/json\//,
        handler: 'StaleWhileRevalidate',
        options: { cacheName: 'df5-data-json', expiration: { maxEntries: 500 } },
      },
      {
        urlPattern: /^\/data\/img\//,
        handler: 'StaleWhileRevalidate',
        options: { cacheName: 'df5-data-img', expiration: { maxEntries: 200 } },
      },
    ],
  },
  manifest: {
    name: 'DarkFindV5',
    short_name: 'DarkFind',
    start_url: '/',
    display: 'standalone',
    background_color: '#141414',
    theme_color: '#1677ff',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
  },
})
```

### 3. 生成 PWA 图标

已用 Pillow 生成最小 192×192 和 512×512 PNG 图标，存放在 `web/public/icons/`。

```bash
cd web && mkdir -p public/icons
python3 -c "
from PIL import Image, ImageDraw, ImageFont
for size, path in [(192,'public/icons/icon-192.png'),(512,'public/icons/icon-512.png')]:
  img = Image.new('RGBA', (size,size), '#1677ff')
  draw = ImageDraw.Draw(img)
  font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size//3)
  bbox = draw.textbbox((0,0), 'DF', font=font)
  tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
  draw.text(((size-tw)/2-bbox[0], (size-th)/2-bbox[1]), 'DF', fill='white', font=font)
  img.save(path, 'PNG')
"

### 4. 注册 Service Worker

`vite-plugin-pwa` 使用 auto 模式：`registerType: 'autoUpdate'`，自动在 index.html 注入注册脚本 `registerSW.js`，`main.tsx` 无需修改。

### 5. 更新 _headers

`public/_headers` 已为 `/assets/*` 设置缓存。SW 接管后浏览器缓存的优先级低于 SW，但保留 _headers 作为兜底。

### 6. 数据版本联动

横幅已移除（缓存由 SW 自动管理），`useDataVersion` 仅用于 `Disclaimer` 显示日期和 `seasonVersion` 用于 localStorage 赛季清理。详见 `docs/CACHE_FIXES.md`。

### 7. `registerSW.js` 预缓存

`registerSW.js` 被加入 `globPatterns`，确保 SW 注册脚本离线可用。`manifest.webmanifest` 和 `icons/*` 由 `vite-plugin-pwa` 自动处理，不重复声明。

### 8. 移除 `navigateFallback`

原始配置使用 `navigateFallback: 'index.html'` 作为离线兜底。但 Workbox 生成的 `NavigationRoute` 在 `NetworkFirst` 之前注册，拦截**所有**导航请求并返回预缓存的 `index.html`（无 SSR 数据），导致 SSG 页面 HTML 永不进入 `df5-html` 缓存。

**修复：** 移除 `navigateFallback`，`NetworkFirst` 正常接管 SSG 路由。访问过的页面离线可正常显示（含 SSR 数据）。未访问的深度链接离线时浏览器报错（可接受权衡，1235 页面全预缓存不现实）。

### 9. SW 更新提示组件

新增 `SWUpdateBanner` 组件（`web/src/components/SWUpdateBanner.tsx`），使用 `workbox-window` 监听 SW 生命周期：
- 首次安装时显示"离线模式已就绪"（5 秒自动消失）
- 使用 `autoUpdate` 模式（SW 安装后自动 `skipWaiting` + `clientsClaim`）
- 因 `self.skipWaiting()` 使 `waiting` 事件永不触发，不显示版本更新提示

### 10. 清理 SW 相关死代码

SW 集成后清理了以下遗留代码：
- 删除 `useRefreshNotice` hook 及横幅相关逻辑
- 删除 5 个页面的 `!dataVersion` useEffect 守卫（`ExplorePage`、`DungeonModuleDetailPage`、`QuestItemsPage`、`QuestItemGroupPage`、`QuestNPCPage`）
- 删除 `HomePage.tsx` 和 `QuestItemGroupPage.tsx` 的 `dataVersion` 调用
- 简化 `SWUpdateBanner` 移除死代码路径

## 无改动的部分

| 文件 | 原因 |
|------|------|
| `ssg.mjs` | SW 不干预 SSG 构建流程 |
| `scripts/` | 无影响 |
| `api/` | 纯后端，无关 |
| `SWUpdateBanner` | 新增组件，使用 `workbox-window` 显示离线就绪提示 |

## 验证方法

```bash
# 构建
cd web && npm run build

# 启动预览
npx vite preview --port 8080 --host 0.0.0.0

# 浏览器验证
# 1. DevTools → Application → Service Workers → 应有 SW 注册
# 2. DevTools → Application → Cache Storage → 应有 df5-data-json / df5-data-img / df5-meta / df5-html
# 3. 已访问页面断网刷新 → 正常加载（NetworkFirst 从缓存服务）
# 4. 未访问深度链接断网 → 浏览器报错（已记录，可接受）
# 5. 重复访问 → Network 面板 /data/json/* 显示 (ServiceWorker)
```

## 回退方案

如果出现问题，回滚只需两步：

```bash
git revert <commit-hash>
cd web && npm uninstall vite-plugin-pwa
```
