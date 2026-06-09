/**
 * SSG build script — full static site generation for DarkFindV5.
 *
 * Steps:
 * 1. Copy data files to public/
 * 2. Build client SPA with Vite
 * 3. Build SSR bundle with Vite (mode=ssr)
 * 4. Read all JSON data files
 * 5. For every route: renderToString → inject into HTML template → save
 * 6. Generate 404.html fallback
 *
 * Usage: node scripts/ssg.mjs
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync, mkdirSync, cpSync } from "fs";
import { join, dirname } from "path";

const WEB = new URL("..", import.meta.url).pathname;
const ROOT = new URL("../../", import.meta.url).pathname;
const DIST = join(WEB, "dist");
const SSR_OUT = join(WEB, "dist-ssr");
const DATA = join(ROOT, "data", "json");

// ---- helpers ----
function readJSON(p) {
  return JSON.parse(readFileSync(p, "utf-8"));
}

// ---- step 0: copy data to public/ ----
console.log("[ssg] copying data to public/…");
cpSync(join(ROOT, "data"), join(WEB, "public", "data"), { recursive: true, force: true });

// ---- step 1: build client ----
console.log("[ssg] building client SPA…");
execSync("npx vite build", { cwd: WEB, stdio: "pipe" });

// ---- step 2: build SSR bundle ----
console.log("[ssg] building SSR bundle…");
execSync("npx vite build --mode ssr", { cwd: WEB, stdio: "pipe" });

// ---- step 3: load SSR renderer ----
const ssrMod = await import(join(SSR_OUT, "ssr.cjs"));
const render = ssrMod.render || ssrMod.default?.render;

// ---- step 4: read all data ----
console.log("[ssg] reading data files…");
const index = readJSON(join(DATA, "index.json"));
const moduleData = readJSON(join(DATA, "dungeon_modules.json"));

const PAGES = ["items", "monsters", "props", "lootdrops"];
const SINGLE = ["explore", "quest_items", "quest_npc"];

// Discover all routes
const routes = [{ path: "/", file: "index.html" }];
for (const p of PAGES) routes.push({ path: `/${p}`, file: `${p}/index.html` });
for (const p of SINGLE) routes.push({ path: `/${p}`, file: `${p}/index.html` });

for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    routes.push({ path: `/${p}/${encodeURIComponent(e.name)}`, file: `${p}/${e.name}/index.html` });
  }
}

// Build per-route data lookup
const ssrDataMap = {};

// Homepage
ssrDataMap["home"] = index;

// List pages
for (const p of PAGES) ssrDataMap[`list-${p}`] = readJSON(join(DATA, `${p}.json`));
for (const p of SINGLE) ssrDataMap[p] = readJSON(join(DATA, `${p}.json`));

// Detail pages — skip entries missing individual JSON
for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    const name = e.name;
    const filePath = p === "lootdrops"
      ? join(DATA, "lootdrops", `${name}.json`)
      : join(DATA, p, `${name}.json`);
    try {
      if (p === "lootdrops") {
        ssrDataMap[`lootdrops/${name}`] = { item: readJSON(filePath), modules: moduleData };
      } else {
        ssrDataMap[`${p}/${name}`] = { entity: readJSON(filePath), modules: moduleData };
      }
    } catch {
      // skip — no individual data file for this entry
    }
  }
}

// ---- step 5: render ----
const template = readFileSync(join(DIST, "index.html"), "utf-8");
console.log(`[ssg] rendering ${routes.length} routes…`);

const t0 = Date.now();
const ROOT_MARKER = '<div id="root">';
const HEAD_CLOSE = "</head>";

/**
 * Map route path to its data key in ssrDataMap.
 */
function routeDataKey(path) {
  if (path === "/") return "home";
  if (path.startsWith("/items/") || path.startsWith("/monsters/") || path.startsWith("/props/")) return path.slice(1);
  if (path.startsWith("/lootdrops/")) return path.slice(1);
  if (path === "/quest_items") return "quest_items";
  if (path === "/quest_npc") return "quest_npc";
  if (path === "/explore") return "explore";
  return `list-${path.slice(1)}`;
}

for (let i = 0; i < routes.length; i++) {
  const r = routes[i];
  const outPath = join(DIST, r.file);
  const urlPath = r.path;
  const dataKey = routeDataKey(urlPath);
  const routeData = ssrDataMap[dataKey];
  const payload = routeData ? { [dataKey]: routeData } : {};

  let page;
  try {
    const result = render(urlPath, ssrDataMap);
    page = template
      .replace(ROOT_MARKER, `<div id="root">${result.html}`)
      .replace(
        HEAD_CLOSE,
        `${result.head}\n<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`
      );
  } catch (err) {
    console.error(`  [err]  ${urlPath}: ${err.message}`);
    // Fallback: serve the shell SPA (client will fetch on its own)
    page = template.replace(
      HEAD_CLOSE,
      `<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`
    );
  }

  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, page, "utf-8");

  if ((i + 1) % 100 === 0 || i === routes.length - 1) {
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`  [${i + 1}/${routes.length}] ${elapsed}s`);
  }
}

// ---- step 6: 404.html ----
writeFileSync(join(DIST, "404.html"), readFileSync(join(DIST, "index.html"), "utf-8"), "utf-8");

const total = ((Date.now() - t0) / 1000).toFixed(1);
console.log(`[ssg] done! ${routes.length} pages in ${total}s`);
