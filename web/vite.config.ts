import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { existsSync, statSync } from "fs";

export default defineConfig(({ mode }) => {
  if (mode === "ssr") {
    // SSR build: bundle src/ssr.tsx for Node.js
    return {
      plugins: [react()],
      base: "./",
      build: {
        ssr: "src/ssr.tsx",
        outDir: "dist-ssr",
        rollupOptions: {
          output: { format: "cjs" },
        },
      },
    };
  }

  // Client build
  return {
    plugins: [
      react(),
      {
        name: "remove-crossorigin",
        transformIndexHtml(html) {
          return html.replaceAll(' crossorigin', "");
        },
      },
      {
        name: "preview-directory-index",
        configurePreviewServer(server) {
          const dist = path.resolve(__dirname, "dist");
          server.middlewares.use((req, res, next) => {
            const url = new URL(req.url, `http://${req.headers.host}`);
            // Skip if already has trailing slash, extension, or is root
            if (url.pathname === "/" || url.pathname.includes(".") || url.pathname.endsWith("/")) {
              return next();
            }
            const dir = path.join(dist, url.pathname);
            const idx = path.join(dir, "index.html");
            if (existsSync(dir) && statSync(dir).isDirectory() && existsSync(idx)) {
              res.writeHead(302, { Location: url.pathname + "/" + url.search });
              return res.end();
            }
            next();
          });
        },
      },
    ],
    base: "./",
    server: {
      fs: {
        allow: [".", "../data"],
      },
    },
    preview: {
      host: "0.0.0.0",
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules")) {
              if (id.includes("antd") || id.includes("@ant-design")) return "antd";
              if (id.includes("react") || id.includes("scheduler") || id.includes("react-dom")) return "react";
            }
          },
        },
      },
    },
  };
});
