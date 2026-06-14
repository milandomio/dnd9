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
 * Usage:
 *   node scripts/ssg.mjs          # full build (861 routes, full SSR)
 *   node scripts/ssg.mjs --quick  # home + list SSG → detail CSR shells (861 routes)
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync, mkdirSync, cpSync, rmSync, statSync, readdirSync } from "fs";
import { join, dirname } from "path";

const QUICK = process.argv.includes("--quick");
const WEB = new URL("..", import.meta.url).pathname;
const ROOT = new URL("../../", import.meta.url).pathname;
const DIST = join(WEB, "dist");
const SSR_OUT = join(WEB, "dist-ssr");
const DATA = join(ROOT, "data", "json");

// ---- helpers ----
function readJSON(p) {
  return JSON.parse(readFileSync(p, "utf-8"));
}

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
const SINGLE = ["explore", "quest_items", "quest_npc", "dungeon_modules"];

// Quest items groups
const questGroups = readJSON(join(DATA, "quest_items_groups.json"));

// ---- step 4a: build search index ----
console.log("[ssg] building search index…");
const searchIndex = [];

for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    const url = p === "lootdrops"
      ? `/lootdrops/${encodeURIComponent(e.name)}`
      : `/${p}/${encodeURIComponent(e.name)}`;
    const entry = { name: e.name, translation: e.translation || "", page: p, url };
    if (p === "lootdrops") {
      entry.variant_count = e.variant_count;
      entry.monsters = e.monsters;
      entry.monster_translations = e.monster_translations;
    }
    searchIndex.push(entry);
  }
}

const exploreData = readJSON(join(DATA, "explore.json"));
for (const e of exploreData) {
  searchIndex.push({
    name: e.name,
    translation: e.npc_name_display || "",
    page: "explore",
    url: "/explore",
  });
}

const questNpcData = readJSON(join(DATA, "quest_npc.json"));
for (const e of questNpcData) {
  searchIndex.push({
    name: e.npc_name,
    translation: e.npc_name_display || "",
    page: "quest_npc",
    url: "/quest_npc",
  });
}

// Dungeon modules search entries
const dmGroupsArr = [...new Set(moduleData.map(m => m.group).filter(Boolean))];
const GROUP_LABELS = {
  Crypt: "废墟2层地牢", FireDeep: "哥布林洞穴2层", GoblinCave: "哥布林洞穴1层",
  IceAbyss: "冰图2层", IceCavern: "冰图1层", Inferno: "废墟3层炼狱",
  Ruins: "废墟1层", ShipGraveyard: "水图", Swamp: "沼泽",
};
for (const g of dmGroupsArr) {
  searchIndex.push({
    name: g,
    translation: GROUP_LABELS[g] || g,
    page: "dungeon_modules",
    url: `/dungeon_modules/${encodeURIComponent(g)}`,
  });
}
for (const m of moduleData) {
  searchIndex.push({
    name: m.name,
    translation: m.translation || m.name,
    page: "dungeon_modules",
    tag: GROUP_LABELS[m.group] || m.group || "模块",
    url: `/dungeon_modules/${encodeURIComponent(m.group || "")}/${encodeURIComponent(m.name)}`,
  });
}

// List/index pages themselves
const LIST_PAGES = [
  { name: "items", translation: "物品表", page: "items", url: "/items" },
  { name: "monsters", translation: "怪物表", page: "monsters", url: "/monsters" },
  { name: "props", translation: "实体表", page: "props", url: "/props" },
  { name: "lootdrops", translation: "掉落表", page: "lootdrops", url: "/lootdrops" },
  { name: "explore", translation: "探索地点表", page: "explore", url: "/explore" },
  { name: "quest_npc", translation: "任务NPC表", page: "quest_npc", url: "/quest_npc" },
  { name: "dungeon_modules", translation: "地图模块表", page: "dungeon_modules", url: "/dungeon_modules" },
];
for (const lp of LIST_PAGES) searchIndex.push(lp);

writeFileSync(join(DATA, "search_index.json"), JSON.stringify(searchIndex), "utf-8");
// Also copy to dist so the deployed site has the latest search index
mkdirSync(join(DIST, "data", "json"), { recursive: true });
cpSync(join(DATA, "search_index.json"), join(DIST, "data", "json", "search_index.json"));
console.log(`[ssg] search index: ${searchIndex.length} entries`);

// ---- step 4b: generate meta.json with latest data date ----
let latestMtime = 0;
function scanDir(dir) {
  for (const f of readdirSync(dir)) {
    const fp = join(dir, f);
    const st = statSync(fp);
    if (st.isDirectory()) scanDir(fp);
    else if (f.endsWith(".json")) latestMtime = Math.max(latestMtime, st.mtimeMs);
  }
}
scanDir(DATA);
const dataDate = String(Math.floor(latestMtime / 1000));
writeFileSync(join(DATA, "meta.json"), JSON.stringify({ dataDate }));
cpSync(join(DATA, "meta.json"), join(DIST, "data", "json", "meta.json"));
console.log(`[ssg] data version: ${dataDate}`);

// Discover all routes — always generate shell files for detail pages (CSR in quick mode)
const routes = [{ path: "/", file: "index.html" }];
for (const p of PAGES) routes.push({ path: `/${p}`, file: `${p}/index.html` });
for (const p of SINGLE) routes.push({ path: `/${p}`, file: `${p}/index.html` });
for (const g of questGroups) {
  routes.push({ path: `/quest_items/${g.group}`, file: `quest_items/${g.group}/index.html` });
}

// Dungeon modules: group pages and module detail pages
const dmGroups = new Set(moduleData.map(m => m.group).filter(Boolean));
for (const g of dmGroups) {
  routes.push({ path: `/dungeon_modules/${g}`, file: `dungeon_modules/${g}/index.html` });
}
for (const m of moduleData) {
  const group = m.group || "";
  routes.push({ path: `/dungeon_modules/${group}/${m.name}`, file: `dungeon_modules/${group}/${m.name}/index.html` });
}

for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    routes.push({ path: `/${p}/${encodeURIComponent(e.name)}`, file: `${p}/${e.name}/index.html` });
  }
}

// Quest NPC detail pages
for (const npc of questNpcData) {
  routes.push({ path: `/quest_npc/${encodeURIComponent(npc.npc_name)}`, file: `quest_npc/${npc.npc_name}/index.html` });
}

// Build per-route data lookup
const ssrDataMap = {};

// Homepage
ssrDataMap["home"] = index;

// List pages
for (const p of PAGES) ssrDataMap[`list-${p}`] = readJSON(join(DATA, `${p}.json`));
for (const p of SINGLE) {
  // quest_items: pipeline-internal, page uses quest_items_groups.json
  // dungeon_modules: page uses useDungeonModules() hook, SSR data not consumed
  if (p === "quest_items" || p === "dungeon_modules") continue;
  ssrDataMap[p] = readJSON(join(DATA, `${p}.json`));
}

// Quest items group detail pages
for (const g of questGroups) {
  if (!QUICK) {
    try {
      const qg = readJSON(join(DATA, "quest_items_groups", `${g.group}.json`));
      ssrDataMap[`quest_items_groups/${g.group}`] = qg;
    } catch {}
  } else {
    ssrDataMap[`quest_items_groups/${g.group}`] = { group: g.group, group_display: g.group_display, entities: [] };
  }
}

// Dungeon modules group pages
for (const g of dmGroupsArr) {
  const groupMods = moduleData.filter(m => m.group === g);
  ssrDataMap[`dungeon_modules/${g}`] = groupMods;
}
// Dungeon modules module data is available globally for detail pages

// Explore page needs module data too
ssrDataMap["explore-modules"] = moduleData;

// Detail pages — full SSR data (full mode) or minimal SSR data (quick mode)
for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    const name = e.name;
    if (!QUICK) {
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
    } else {
      // Quick mode: inject minimal metadata for SEO (name + translation only)
      if (p === "lootdrops") {
        ssrDataMap[`lootdrops/${name}`] = { item: { name: e.name, translation: e.translation } };
      } else {
        ssrDataMap[`${p}/${name}`] = { entity: { name: e.name, translation: e.translation } };
      }
    }
  }
}

// ---- step 5: render ----
const template = readFileSync(join(DIST, "index.html"), "utf-8");
console.log(`[ssg] rendering ${routes.length} routes…`);

const t0 = Date.now();
console.log(`[ssg] mode=${QUICK ? "quick" : "full"} — ${routes.length} routes`);
const ROOT_MARKER = '<div id="root">';
const HEAD_CLOSE = "</head>";

/**
 * Map route path to its data key in ssrDataMap.
 */
function routeDataKey(path) {
  if (path === "/") return "home";
  if (path.startsWith("/items/") || path.startsWith("/monsters/") || path.startsWith("/props/")) return path.slice(1);
  if (path.startsWith("/lootdrops/")) return path.slice(1);
  if (path.startsWith("/quest_items/")) return `quest_items_groups/${path.split("/")[2]}`;
  if (path === "/quest_items") return "quest_items";
  if (path === "/quest_npc") return "quest_npc";
  if (path.startsWith("/quest_npc/")) return "quest_npc";
  if (path === "/dungeon_modules") return "dungeon_modules";
  if (path.startsWith("/dungeon_modules/")) {
    const parts = path.split("/");
    if (parts.length === 3) return `dungeon_modules/${parts[2]}`;
    return ""; // detail pages: no SSR data needed
  }
  if (path === "/explore") return "explore";
  return `list-${path.slice(1)}`;
}

/**
 * Compute <base href="..."> value from output file path relative to dist root.
 */
function baseHrefFromFile(_file) {
  return "/";
}

for (let i = 0; i < routes.length; i++) {
  const r = routes[i];
  const outPath = join(DIST, r.file);
  const urlPath = r.path;
  const baseHref = baseHrefFromFile(r.file);
  const dataKey = routeDataKey(urlPath);
  const routeData = ssrDataMap[dataKey];

  // Base tag must be first in <head> so script/link assets resolve correctly.
  const templated = template.replace("</title>", `</title>\n    <base href="${baseHref}">`);

  let page;
  if (routeData) {
    const payload = { [dataKey]: routeData };
    try {
      const result = render(urlPath, ssrDataMap);
      const headlessTemplate = templated.replace(/<title>[^<]*<\/title>\s*/, "");
      page = headlessTemplate
        .replace(ROOT_MARKER, `<div id="root">${result.html}`)
        .replace(HEAD_CLOSE, `${result.head}\n<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`);
    } catch (err) {
      console.error(`  [err]  ${urlPath}: ${err.message}`);
      page = templated.replace(HEAD_CLOSE, `<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`);
    }
  } else {
    page = templated.replace(HEAD_CLOSE, `\n</head>`);
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

// ---- step 7: cleanup SSR bundle ----
rmSync(SSR_OUT, { recursive: true, force: true });
console.log("[ssg] SSR build cleaned up");

const total = ((Date.now() - t0) / 1000).toFixed(1);
console.log(`[ssg] done! ${routes.length} pages in ${total}s (mode=${QUICK ? "quick" : "full"})`);
