import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { existsSync, statSync } from 'fs';

export default defineConfig(({ mode }) => {
  if (mode === 'ssr') {
    // SSR build: bundle src/ssr.tsx for Node.js
    return {
      plugins: [react()],
      build: {
        ssr: 'src/ssr.tsx',
        outDir: 'dist-ssr',
        rollupOptions: {
          output: { format: 'cjs' },
        },
      },
    };
  }

  // Client build
  return {
    plugins: [
      react(),
      {
        name: 'inject-versioned-preload',
        transformIndexHtml(html) {
          const ver = process.env.VITE_DATA_VERSION;
          let out = html.replaceAll(' crossorigin', '');
          if (!ver) return out;
          const short = Number(ver).toString(36);
          const preloads = [
            `<link rel="preload" href="/data/json/meta.json" as="fetch" crossorigin="anonymous">`,
            `<link rel="preload" href="/data/${short}/json/dungeon_modules.json" as="fetch" crossorigin="anonymous">`,
          ];
          return out.replace(
            '</title>',
            `</title>\n    ${preloads.join('\n    ')}`
          );
        },
      },
      VitePWA({
        registerType: 'prompt',
        workbox: {
          // registerSW.js 预缓存确保 SW 注册脚本离线可用；
          // manifest.webmanifest 和 icons/ 由 VitePWA 自动处理，不重复声明；
          // index.html/404.html 在 SSG 阶段才生成，构建时不存在，不走预缓存。
          // navigateFallback 未启用：SSG 路由的独立 HTML（含 SSR 数据）由 NetworkFirst 接管，
          // 访问后缓存，离线重复访问正常显示（含 SSR 数据）；首次离线深度链接无缓存时浏览器报错。
          navigateFallback: undefined,
          globPatterns: [
            'assets/**/*.{js,css}',
            'registerSW.js',
            'offline.html',
          ],
          runtimeCaching: [
            {
              // Version-based invalidation via refreshNow() clears df5-* caches;
              // no maxAgeSeconds needed — cache lives until user triggers refresh.
              urlPattern: ({ request }) => request.mode === 'navigate',
              handler: 'NetworkFirst',
              options: {
                cacheName: 'df5-html',
                expiration: { maxEntries: 1300 },
              },
            },
            {
              // meta.json: 5-minute TTL so version change is detected within reasonable time
              urlPattern: ({ url }) => url.pathname === '/data/json/meta.json',
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'df5-meta',
                expiration: { maxEntries: 1, maxAgeSeconds: 300 },
              },
            },
            {
              urlPattern: ({ url }) => url.pathname.startsWith('/data/json/'),
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'df5-data-json',
                expiration: { maxEntries: 3300 },
              },
            },
            {
              urlPattern: ({ url }) => url.pathname.startsWith('/data/img/'),
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'df5-data-img',
                expiration: { maxEntries: 300 },
              },
            },
          ],
        },
        manifest: {
          name: 'DND闪电指南',
          short_name: 'DND闪电指南',
          description: '闪电指南-游戏地图-任务攻略-BOSS掉落-资源点位-寻找宝箱',
          lang: 'zh-Hans',
          start_url: '/',
          display: 'standalone',
          background_color: '#141414',
          theme_color: '#1677ff',
          categories: ['games', 'utilities'],
          orientation: 'any',
          icons: [
            {
              src: '/icons/icon-192-v2.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any maskable',
            },
            {
              src: '/icons/icon-512-v2.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any maskable',
            },
          ],
        },
      }),
      {
        name: 'preview-directory-index',
        configurePreviewServer(server) {
          const dist = path.resolve(__dirname, 'dist');
          server.middlewares.use((req, res, next) => {
            const url = new URL(req.url, `http://${req.headers.host}`);
            // Skip if already has trailing slash, extension, or is root
            if (
              url.pathname === '/' ||
              url.pathname.includes('.') ||
              url.pathname.endsWith('/')
            ) {
              return next();
            }
            const dir = path.join(dist, url.pathname);
            const idx = path.join(dir, 'index.html');
            if (
              existsSync(dir) &&
              statSync(dir).isDirectory() &&
              existsSync(idx)
            ) {
              res.writeHead(302, { Location: url.pathname + '/' + url.search });
              return res.end();
            }
            next();
          });
        },
      },
    ],
    base: '/',
    server: {
      fs: {
        allow: ['.', '../data'],
      },
    },
    preview: {
      host: '0.0.0.0',
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('antd') || id.includes('@ant-design'))
                return 'antd';
              if (
                id.includes('react') ||
                id.includes('scheduler') ||
                id.includes('react-dom')
              )
                return 'react';
            }
          },
        },
      },
    },
  };
});
