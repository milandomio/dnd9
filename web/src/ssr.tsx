/**
 * SSR entry – called by the SSG build script.
 *
 * Renders a React route to HTML string + head tags
 * using renderToString + StaticRouter.
 *
 * NOTE: Ant Design v5 accesses browser globals (document, window)
 * during rendering. We stub them here so renderToString works in Node.
 */
import React from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { HelmetProvider } from "react-helmet-async";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import { ThemeProvider } from "./hooks/useTheme";
import { DebugProvider } from "./hooks/useDebug";
import SSRDataContext from "./context/SSRDataContext";
import { AppInner } from "./App";

// Ant Design v5+ requires browser-global stubs for SSR
globalThis.window = globalThis;
globalThis.document = {
  createElement: () => ({ className: "", setAttribute: () => {} }),
  createTextNode: () => ({}),
  getElementsByTagName: () => [],
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: { style: {} },
  head: { appendChild: () => {}, querySelectorAll: () => [] },
  body: { appendChild: () => {} },
} as any;
globalThis.navigator = { userAgent: "node" } as any;
globalThis.location = { href: "", pathname: "", search: "", hash: "" } as any;

export function render(url: string, ssrDataMap: Record<string, any>) {
  const helmetContext: Record<string, any> = {};

  const html = renderToString(
    <HelmetProvider context={helmetContext}>
      <ConfigProvider
        locale={zhCN}
        theme={{ algorithm: theme.darkAlgorithm, token: { colorPrimary: "#1677ff" } }}
      >
        <ThemeProvider>
          <DebugProvider>
            <SSRDataContext.Provider value={ssrDataMap}>
              <StaticRouter location={url}>
                <AppInner />
              </StaticRouter>
            </SSRDataContext.Provider>
          </DebugProvider>
        </ThemeProvider>
      </ConfigProvider>
    </HelmetProvider>
  );

  const { helmet } = helmetContext;

  return {
    html,
    head: [
      helmet?.title?.toString() ?? "",
      helmet?.meta?.toString() ?? "",
    ].join("").trim(),
  };
}
