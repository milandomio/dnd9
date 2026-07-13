# Service Worker 集成记录

## 状态：已完成 (2026-07-14)

为静态网站添加了离线缓存和运行时网络策略，同时修复了缓存机制中的若干问题（详见 `CACHE_FIXES.md`）。

> **缓存策略**: SW 运行时缓存无时间过期（`?v=` 版本参数自然绕过旧缓存键）；CDN/HTTP 层 asset 永久、JSON `no-cache`。

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
  registerType: 'autoUpdate',     // SW 更新后自动接管
  workbox: {
    // 不包含 index.html — 避免 Workbox 自动添加 NavigationRoute 覆盖 SSG 路由
    globPatterns: ['assets/**/*.{js,css}'],
    runtimeCaching: [
      // 版本变化由 refreshNow() 清除 df5-* 缓存，无需 maxAgeSeconds
      {
        urlPattern: /^\/data\/json\//,
        handler: 'StaleWhileRevalidate',
        options: { cacheName: 'df5-data-json', expiration: { maxEntries: 500 } },
      },
      // 地图图片：大文件，优先缓存
      {
        urlPattern: /^\/data\/img\//,
        handler: 'CacheFirst',
        options: { cacheName: 'df5-data-img', expiration: { maxEntries: 200 } },
      },
      // SSG HTML 页面：NetworkFirst（导航请求，不包含 .html 后缀）
      {
        urlPattern: ({ request }) => request.mode === 'navigate',
        handler: 'NetworkFirst',
        options: { cacheName: 'df5-html', expiration: { maxEntries: 200 } },
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

## 无改动的部分

| 文件 | 原因 |
|------|------|
| `ssg.mjs` | SW 不干预 SSG 构建流程 |
| `scripts/` | 无影响 |
| `api/` | 纯后端，无关 |
| 组件代码 | PWA 对 React 组件透明 |

## 验证方法

```bash
# 构建
cd web && npm run build

# 启动预览
npx vite preview --port 8080 --host 0.0.0.0

# 浏览器验证
# 1. DevTools → Application → Service Workers → 应有 SW 注册
# 2. DevTools → Application → Cache Storage → 应有 df5-data-json / df5-data-img / df5-html
# 3. 断网刷新 → 页面应正常加载
# 4. 重复访问 → Network 面板 /data/json/* 显示 (ServiceWorker)
```

## 回退方案

如果出现问题，回滚只需两步：

```bash
git revert <commit-hash>
cd web && npm uninstall vite-plugin-pwa
```
