import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
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
});
