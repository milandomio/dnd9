/**
 * Lightweight Playwright prerender for DarkFindV5.
 *
 * Prerenders only top-level pages for SEO: homepage + 7 list pages.
 * Detail pages use the 404.html SPA fallback (React client-side route).
 */

import { chromium } from "playwright";
import { createServer } from "http";
import { readFileSync, existsSync, statSync, mkdirSync, writeFileSync } from "fs";
import { join, extname } from "path";

const DIST = new URL("../dist/", import.meta.url).pathname;
const PORT = 4175;
const BASE = `http://localhost:${PORT}`;

// Only prerender these routes — everything else falls through to SPA
const ROUTES = [
  "/",
  "/items",
  "/monsters",
  "/props",
  "/lootdrops",
  "/explore",
  "/quest_items",
  "/quest_npc",
];

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".webp": "image/webp",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

let server;

function startServer() {
  return new Promise((resolve) => {
    server = createServer((req, res) => {
      const p = new URL(req.url, BASE).pathname;
      let fp = join(DIST, p);
      if (existsSync(fp) && statSync(fp).isDirectory()) fp = join(fp, "index.html");
      try {
        if (!existsSync(fp)) { res.writeHead(404); res.end("Not found"); return; }
        res.writeHead(200, { "Content-Type": MIME[extname(fp)] || "application/octet-stream" });
        res.end(readFileSync(fp));
      } catch { res.writeHead(404); res.end("Not found"); }
    });
    server.listen(PORT, "127.0.0.1", resolve);
  });
}
function stopServer() { server?.close(); server = null; }

function createDirPlaceholders() {
  // Create directory-based index.html with correct base for each list route
  const rootHtml = readFileSync(join(DIST, "index.html"), "utf-8");
  const withBase = rootHtml.replace("<head>", '<head><base href="/">');
  writeFileSync(join(DIST, "index.html"), withBase, "utf-8");

  for (const route of ROUTES) {
    if (route === "/") continue;
    const depth = route.split("/").filter(Boolean).length;
    const prefix = "../".repeat(depth);
    let html = rootHtml.replace(
      /(src|href)=("|')(\.\/)([^"']*)\2/g,
      (_, a, q, _ds, path) => `${a}=${q}${prefix}${path}${q}`
    );
    html = html.replace("<head>", '<head><base href="/">');
    const out = join(DIST, route.slice(1), "index.html");
    mkdirSync(join(DIST, route.slice(1)), { recursive: true });
    writeFileSync(out, html, "utf-8");
  }
}

async function main() {
  console.log("[prerender] creating directory placeholders...");
  createDirPlaceholders();

  console.log("[prerender] starting server...");
  await startServer();

  console.log("[prerender] launching browser...");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-gpu"] });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await ctx.newPage();

  const t0 = Date.now();
  let ok = 0, err = 0;

  for (const route of ROUTES) {
    const url = `${BASE}${route}`;
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 25000 });
      await page.waitForFunction(
        () => !document.querySelector(".ant-spin-spinning"),
        { timeout: 10000 }
      ).catch(() => {});
      await page.waitForTimeout(200);
      const html = await page.content();

      if (route === "/") {
        writeFileSync(join(DIST, "index.html"), html, "utf-8");
      } else {
        writeFileSync(join(DIST, route.slice(1), "index.html"), html, "utf-8");
      }
      console.log(`  [ok] ${route}`);
      ok++;
    } catch (e) {
      console.error(`  [err] ${route}: ${e.message}`);
      err++;
    }
  }

  // 404 fallback (same as homepage content, for SPA routing)
  const idx = readFileSync(join(DIST, "index.html"), "utf-8");
  writeFileSync(join(DIST, "404.html"), idx, "utf-8");

  await browser.close();
  stopServer();

  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`[prerender] done! ${ok} ok, ${err} err in ${elapsed}s`);
}

main().catch((e) => { console.error("[fatal]", e); stopServer(); process.exit(1); });
