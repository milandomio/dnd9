/**
 * SSG build script — static site generation for DarkFindV5.
 *
 * Generates route HTML files from the client SPA template.
 * No SSR data inlining — all data fetched at runtime by the client.
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync, mkdirSync, cpSync } from "fs";
import { join } from "path";

const WEB = new URL("..", import.meta.url).pathname;
const DIST = join(WEB, "dist");
const DATA = join(WEB, "public", "data");

function readJSON(p) {
  return JSON.parse(readFileSync(p, "utf-8"));
}

// Step 1: copy data to public/
console.log("[ssg] copying data to public/\u2026");
cpSync(join(WEB, "..", "data"), join(WEB, "public", "data"), { recursive: true, force: true });

// Step 2: build client SPA
console.log("[ssg] building client SPA\u2026");
execSync("npx vite build", { cwd: WEB, stdio: "pipe" });

// Step 3: discover all routes
const PAGES = ["items", "monsters", "props", "lootdrops"];
const SINGLE = ["explore", "quest_items", "quest_npc"];

const routes = [{ path: "/", file: "index.html" }];
for (const p of PAGES) routes.push({ path: `/${p}`, file: `${p}/index.html` });
for (const p of SINGLE) routes.push({ path: `/${p}`, file: `${p}/index.html` });

for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    routes.push({ path: `/${p}/${encodeURIComponent(e.name)}`, file: `${p}/${e.name}/index.html` });
  }
}

// Step 4: generate HTML files from template
const template = readFileSync(join(DIST, "index.html"), "utf-8");

function baseHrefFromFile(file) {
  const depth = (file.match(/\//g) || []).length;
  return depth === 0 ? "./" : "../".repeat(depth);
}

console.log(`[ssg] generating ${routes.length} routes\u2026`);
for (const r of routes) {
  const baseHref = baseHrefFromFile(r.file);
  const html = template.replace("</title>", `</title>\n    <base href="${baseHref}">`);
  const outPath = join(DIST, r.file);
  mkdirSync(join(outPath, ".."), { recursive: true });
  writeFileSync(outPath, html, "utf-8");
}

// Step 5: 404.html
writeFileSync(join(DIST, "404.html"), template, "utf-8");

// Step 6: cleanup public/data copy
// (keep it — needed for runtime fetch)
console.log(`[ssg] done! ${routes.length} pages`);
