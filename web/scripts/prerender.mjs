/**
 * Playwright-based prerender script for DarkFindV5.
 *
 * 1. Signs built SPA (web/dist/) and starts a static server with SPA fallback
 * 2. Uses Playwright to navigate every route, wait for content to render
 * 3. Saves the final HTML to the correct dist subdirectory
 * 4. Also generates dist/404.html for GitHub Pages SPA fallback
 *
 * Usage: node scripts/prerender.mjs
 * Requires: npm run build first
 */

import { chromium } from "playwright";
import { createServer } from "http";
import { readFileSync, existsSync, mkdirSync, writeFileSync, cpSync } from "fs";
import { join, dirname, extname } from "path";
import { spawn } from "child_process";

const DIST = new URL("../dist/", import.meta.url).pathname;
const DATA = new URL("../data/json/", import.meta.url).pathname;
const PORT = 4175; // avoid conflict with vite preview default 4173
const BASE = `http://localhost:${PORT}`;

// --------------- route discovery ---------------

function readJSON(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function buildRoutes() {
  // Static list pages + detail sub-pages
  const PAGES = ["items", "monsters", "props", "lootdrops"];
  const SINGLE_PAGES = ["explore", "quest_items", "quest_npc"];

  const routes = [];

  // Homepage
  routes.push({ path: "/", file: "index.html" });

  // List pages
  for (const p of PAGES) {
    routes.push({ path: `/${p}`, file: `${p}/index.html` });
  }
  for (const p of SINGLE_PAGES) {
    routes.push({ path: `/${p}`, file: `${p}/index.html` });
  }

  // Detail pages
  for (const p of PAGES) {
    try {
      const list = readJSON(join(DATA, `${p}.json`));
      for (const entry of list) {
        const name = entry.name;
        routes.push({
          path: `/${p}/${encodeURIComponent(name)}`,
          file: `${p}/${name}/index.html`,
        });
      }
    } catch (e) {
      console.warn(`  [warn] could not read ${p}.json: ${e.message}`);
    }
  }

  return routes;
}

// --------------- SPA server ---------------

let server;
function startServer() {
  return new Promise((resolve) => {
    server = createServer((req, res) => {
      let urlPath = new URL(req.url, BASE).pathname;
      // Default to index.html for root
      if (urlPath === "/") urlPath = "/index.html";

      // Determine file path
      let filePath = join(DIST, urlPath);

      // If the path has no extension, treat as SPA route: serve index.html
      if (!extname(urlPath) && !urlPath.endsWith("/")) {
        filePath = join(DIST, "index.html");
      }

      // Check if file exists
      if (!existsSync(filePath)) {
        filePath = join(DIST, "index.html");
      }

      try {
        const content = readFileSync(filePath);
        const mime = {
          ".html": "text/html; charset=utf-8",
          ".js": "application/javascript",
          ".css": "text/css",
          ".json": "application/json",
          ".png": "image/png",
          ".jpg": "image/jpeg",
          ".webp": "image/webp",
          ".svg": "image/svg+xml",
          ".ico": "image/x-icon",
        }[extname(filePath)] || "application/octet-stream";

        res.writeHead(200, { "Content-Type": mime });
        res.end(content);
      } catch (e) {
        res.writeHead(404);
        res.end("Not found");
      }
    });

    server.listen(PORT, "127.0.0.1", () => {
      console.log(`  [server] listening on http://127.0.0.1:${PORT}`);
      resolve();
    });
  });
}

function stopServer() {
  if (server) {
    server.close();
    server = null;
  }
}

// --------------- prerender ---------------

async function prerenderPage(browser, route, concurrency) {
  const { path, file } = route;
  const url = `${BASE}${path}`;
  const outPath = join(DIST, file);

  // Ensure directory exists
  mkdirSync(dirname(outPath), { recursive: true });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });

    // Additional wait for React hydration & ant-spin to disappear
    try {
      await page.waitForFunction(
        () => {
          const spins = document.querySelectorAll(".ant-spin");
          return spins.length === 0 || Array.from(spins).every((s) => s.style.display === "none");
        },
        { timeout: 10000 }
      );
    } catch {
      // timeout is fine; content may render without ant-spin
    }

    // Small settle time for images / rendering
    await page.waitForTimeout(500);

    // Capture the full HTML
    const html = await page.content();

    // Only write if we got meaningful content (not just a spinner)
    if (html.includes("DarkFindV5") || html.includes("<h1") || html.includes("section-content")) {
      writeFileSync(outPath, html, "utf-8");
      console.log(`  [ok]   ${url} -> ${file}`);
    } else {
      // Fallback: write anyway with a warning
      writeFileSync(outPath, html, "utf-8");
      console.warn(`  [warn] ${url} -> ${file} (content may be incomplete)`);
    }
  } catch (err) {
    console.error(`  [err]  ${url} -> ${err.message}`);
  } finally {
    await context.close();
  }
}

async function main() {
  console.log("[prerender] discovering routes...");
  const allRoutes = buildRoutes();
  console.log(`[prerender] found ${allRoutes.length} routes`);

  // Ensure dist/data exists with JSON files
  // (they're copied by the prebuild script already)
  if (!existsSync(join(DIST, "data"))) {
    console.error("[prerender] dist/data/ not found. Did you forget 'npm run build'?");
    process.exit(1);
  }

  console.log("[prerender] starting SPA server...");
  await startServer();

  console.log("[prerender] launching Playwright...");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu"],
  });

  const CONCURRENCY = 10;
  const startTime = Date.now();
  let done = 0;

  try {
    // Process in batches
    for (let i = 0; i < allRoutes.length; i += CONCURRENCY) {
      const batch = allRoutes.slice(i, i + CONCURRENCY);
      const promises = batch.map((route) => prerenderPage(browser, route, CONCURRENCY));
      await Promise.allSettled(promises);
      done += batch.length;
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`  [batch] ${done}/${allRoutes.length} done (${elapsed}s)`);
    }

    // ======= Generate 404.html for GitHub Pages SPA fallback =======
    // The homepage prerendered content serves as the 404 fallback.
    // On GitHub Pages, visiting /items/NonExistent will serve 404.html,
    // which loads the SPA and client-side routes to the correct page.
    try {
      const homeHtml = readFileSync(join(DIST, "index.html"), "utf-8");
      writeFileSync(join(DIST, "404.html"), homeHtml, "utf-8");
      console.log("[prerender] 404.html generated from index.html");
    } catch (e) {
      console.warn(`[prerender] could not generate 404.html: ${e.message}`);
    }

    const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`\n[prerender] done! ${done}/${allRoutes.length} pages in ${totalTime}s`);
  } finally {
    await browser.close();
    stopServer();
  }
}

main().catch((err) => {
  console.error("[prerender] fatal:", err);
  stopServer();
  process.exit(1);
});
