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

// ---- step 4: generate meta.json with latest data date ----
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
    if (p === 'lootdrops' && e.variant_suffixes && e.variant_suffixes.length > 1) {
      // Base lootdrop entry (e.g. "HeaterShield") redirects to default variant;
      // generate a minimal redirect page, then create per-suffix variant pages.
      const defaultSuffix = e.variant_suffixes.includes('5001') ? '5001' : e.variant_suffixes[0];
      const target = `/lootdrops/${e.name}_${defaultSuffix}/`;
      routes.push({
        path: `/${p}/${encodeURIComponent(e.name)}`,
        file: `${p}/${e.name}/index.html`,
        redirect: target,
      });
      for (const suffix of e.variant_suffixes) {
        const variantName = `${e.name}_${suffix}`;
        routes.push({ path: `/lootdrops/${encodeURIComponent(variantName)}`, file: `lootdrops/${variantName}/index.html` });
      }
    } else {
      routes.push({ path: `/${p}/${encodeURIComponent(e.name)}`, file: `${p}/${e.name}/index.html` });
    }
  }
}

// Quest NPC detail pages
const questNpcData = readJSON(join(DATA, "quest_npc.json"));
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
  // dungeon_modules: page uses useDungeonModules() hook, SSR data not consumed
  if (p === "dungeon_modules") continue;
  // quest_items: pipeline-internal file, use quest_items_groups.json instead
  if (p === "quest_items") {
    ssrDataMap[p] = readJSON(join(DATA, "quest_items_groups.json"));
    continue;
  }
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
for (const g of dmGroups) {
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
          const itemData = { item: readJSON(filePath), modules: moduleData };
          ssrDataMap[`lootdrops/${name}`] = itemData;
          // Read variant-specific detail files
          if (e.variant_suffixes && e.variant_suffixes.length > 1) {
            for (const suffix of e.variant_suffixes) {
              const variantFile = join(DATA, "lootdrops", `${name}_${suffix}.json`);
              try {
                ssrDataMap[`lootdrops/${name}_${suffix}`] = { item: readJSON(variantFile), modules: moduleData };
              } catch {
                ssrDataMap[`lootdrops/${name}_${suffix}`] = itemData;
              }
            }
          }
        } else {
          ssrDataMap[`${p}/${name}`] = { entity: readJSON(filePath), modules: moduleData };
        }
      } catch {
        // skip — no individual data file for this entry
      }
    } else {
      // Quick mode: inject minimal metadata for SEO (name + translation only)
      if (p === "lootdrops") {
        const minimalItem = { item: { name: e.name, translation: e.translation } };
        ssrDataMap[`lootdrops/${name}`] = minimalItem;
        if (e.variant_suffixes && e.variant_suffixes.length > 1) {
          for (const suffix of e.variant_suffixes) {
            ssrDataMap[`lootdrops/${name}_${suffix}`] = minimalItem;
          }
        }
      } else {
        ssrDataMap[`${p}/${name}`] = { entity: { name: e.name, translation: e.translation } };
      }
    }
  }
}

// ---- step 4b: P005 — preload referenced entity coords for lootdrop detail pages ----
if (!QUICK) {
  console.log("[ssg] preloading referenced coords for lootdrop detail pages…");
  let refCount = 0;
  for (const [key, data] of Object.entries(ssrDataMap)) {
    if (!key.startsWith("lootdrops/")) continue;
    const item = data.item;
    if (!item?.monsters) continue;

    const refCoordsMap = {};
    for (const m of item.monsters) {
      if (!m.ref) continue;
      const refFile = join(DATA, `${m.ref}.json`);
      try {
        const refEntity = readJSON(refFile);
        refCoordsMap[m.ref] = Array.isArray(refEntity) ? refEntity : (refEntity.coords || []);
        refCount++;
      } catch {
        // skip — ref entity file not found
      }
    }
    if (Object.keys(refCoordsMap).length > 0) {
      data._refCoords = refCoordsMap;
    }
  }
  console.log(`[ssg] preloaded ${refCount} ref coords for lootdrop pages`);
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
  if (path.startsWith("/lootdrops/")) {
    return `lootdrops/${decodeURIComponent(path.slice("/lootdrops/".length))}`;
  }
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
  // Canonical URL with trailing slash for SEO
  const canonical = urlPath === "/" ? "/" : urlPath.replace(/\/?$/, "/");
  const templated = template.replace("</title>", `</title>\n    <link rel="canonical" href="${canonical}">\n    <base href="${baseHref}">`);

  let page;
  if (r.redirect) {
    const title = `${r.file.split("/")[1]} — DarkFind`;
    page = `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>${title}</title>
<link rel="canonical" href="${r.redirect}">
<meta http-equiv="refresh" content="0;url=${r.redirect}"></head>
<body><script>window.location.replace("${r.redirect}");</script></body>
</html>`;
  } else if (routeData) {
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

// ---- step 7: cleanup SSR bundle and manifest ----
rmSync(SSR_OUT, { recursive: true, force: true });
try { rmSync(join(DIST, ".vite"), { recursive: true, force: true }); } catch {}
console.log("[ssg] SSR build cleaned up");

// ---- step 8: sitemap.xml ----
const SITE = "https://dnd9.icetar.com";
const dataDateStr = new Date(Number(dataDate) * 1000).toISOString().split("T")[0];

function sitemapPriority(path) {
  if (path === "/") return ["1.0", "daily"];
  if (path === "/explore") return ["0.7", "weekly"];
  if (path.startsWith("/items/") || path.startsWith("/monsters/") || path.startsWith("/props/")) return ["0.6", "weekly"];
  if (path.startsWith("/lootdrops/")) return ["0.5", "weekly"];
  if (path.startsWith("/dungeon_modules/")) return ["0.5", "weekly"];
  if (path.startsWith("/quest_")) return ["0.4", "monthly"];
  // list pages
  if (path.split("/").length <= 2) return ["0.8", "weekly"];
  return ["0.3", "monthly"];
}

let sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n';
sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
for (const r of routes) {
  if (r.redirect) continue;
  const loc = SITE + (r.path === "/" ? "/" : r.path.replace(/\/?$/, "/"));
  const [prio, freq] = sitemapPriority(r.path);
  sitemap += `  <url>\n    <loc>${loc}</loc>\n    <lastmod>${dataDateStr}</lastmod>\n    <changefreq>${freq}</changefreq>\n    <priority>${prio}</priority>\n  </url>\n`;
}
sitemap += '</urlset>\n';
writeFileSync(join(DIST, "sitemap.xml"), sitemap, "utf-8");
console.log(`[ssg] sitemap.xml generated (${routes.length - routes.filter(r => r.redirect).length} URLs)`);

const total = ((Date.now() - t0) / 1000).toFixed(1);
console.log(`[ssg] done! ${routes.length} pages in ${total}s (mode=${QUICK ? "quick" : "full"})`);
