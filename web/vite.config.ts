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
        name: 'remove-crossorigin',
        transformIndexHtml(html) {
          return html.replaceAll(' crossorigin', '');
        },
      },
      VitePWA({
        registerType: 'autoUpdate',
        workbox: {
          // Empty string disables VitePWA's default navigateFallback:'index.html',
          // which would create a NavigationRoute serving root index.html for all
          // SSG routes, breaking SSR data injection.
          navigateFallback: '',
          globPatterns: ['assets/**/*.{js,css}'],
          runtimeCaching: [
            {
              // Version-based invalidation via refreshNow() clears df5-* caches;
              // no maxAgeSeconds needed — cache lives until user triggers refresh.
              urlPattern: ({ request }) => request.mode === 'navigate',
              handler: 'NetworkFirst',
              options: {
                cacheName: 'df5-html',
                expiration: { maxEntries: 200 },
              },
            },
            {
              urlPattern: /^\/data\/json\//,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'df5-data-json',
                expiration: { maxEntries: 500 },
              },
            },
            {
              urlPattern: /^\/data\/img\//,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'df5-data-img',
                expiration: { maxEntries: 200 },
              },
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
            {
              src: '/icons/icon-192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: '/icons/icon-512.png',
              sizes: '512x512',
              type: 'image/png',
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
