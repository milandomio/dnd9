import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
    ],
    base: "./",
    server: {
      fs: {
        allow: [".", "../data"],
      },
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
