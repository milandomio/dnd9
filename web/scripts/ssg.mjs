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

import { execSync } from 'child_process';
import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  cpSync,
  rmSync,
  statSync,
  readdirSync,
} from 'fs';
import { join, dirname } from 'path';
import { buildSeoDescription } from '../src/i18n/seoTemplate.mjs';

const QUICK = process.argv.includes('--quick');
const WEB = new URL('..', import.meta.url).pathname;
const ROOT = new URL('../../', import.meta.url).pathname;
const DIST = join(WEB, 'dist');
const SSR_OUT = join(WEB, 'dist-ssr');
const DATA = join(ROOT, 'data', 'json');
const SITE = 'https://dnd9.icetar.com';
const BASE = process.env.VITE_BASE || '/';
const HOME_TITLE_DESCRIPTIONS = {
  'zh-Hans': '游戏地图·任务攻略·BOSS掉落·资源点位·寻找宝箱',
  en: 'Game Maps · Quest Guides · Boss Drops · Resource Locations · Find Chests',
  de: 'Spielkarten · Quest-Guides · Boss-Drops · Ressourcenfundorte · Truhen finden',
  es: 'Mapas del juego · Guías de misiones · Botín de jefes · Ubicaciones de recursos · Encontrar cofres',
  fr: 'Cartes du jeu · Guides de quêtes · Butin des boss · Emplacements des ressources · Trouver des coffres',
  ja: 'ゲームマップ · クエスト攻略 · ボスドロップ · 資源ポイント · 宝箱を探す',
  ko: '게임 지도 · 퀘스트 공략 · 보스 드롭 · 자원 위치 · 보물상자 찾기',
  'pt-BR':
    'Mapas do jogo · Guias de missões · Drops de chefes · Localizações de recursos · Encontrar baús',
  ru: 'Карты игры · Гайды по заданиям · Добыча с боссов · Места ресурсов · Поиск сундуков',
  'zh-Hant': '遊戲地圖 · 任務攻略 · BOSS掉落 · 資源點位 · 尋找寶箱',
};

// ---- helpers ----
function readJSON(p) {
  return JSON.parse(readFileSync(p, 'utf-8'));
}

// ---- step 0: compute data version ----
let latestMtime = 0;
function scanDir(dir) {
  for (const f of readdirSync(dir)) {
    const fp = join(dir, f);
    const st = statSync(fp);
    if (st.isDirectory()) scanDir(fp);
    else if (f.endsWith('.json'))
      latestMtime = Math.max(latestMtime, st.mtimeMs);
  }
}
scanDir(DATA);
const dataDate = String(Math.floor(latestMtime / 1000));
process.env.VITE_DATA_VERSION = dataDate;
console.log(`[ssg] data version: ${dataDate}`);

// ---- step 1: build client ----
console.log('[ssg] building client SPA…');
execSync('node node_modules/.bin/vite build', { cwd: WEB, stdio: 'pipe' });

// ---- step 1.5: create versioned data copies for CDN cache busting ----
const shortVer = Number(dataDate).toString(36);
const publicJsonDir = join(DIST, 'data', 'json');
const vJsonDir = join(DIST, 'data', shortVer, 'json');
mkdirSync(vJsonDir, { recursive: true });
function copyDeep(src, dest) {
  for (const f of readdirSync(src)) {
    const sp = join(src, f);
    const dp = join(dest, f);
    const st = statSync(sp);
    if (st.isDirectory()) {
      mkdirSync(dp, { recursive: true });
      copyDeep(sp, dp);
    } else {
      cpSync(sp, dp);
    }
  }
}
// Write meta.json before copying so /data/json/meta.json remains available for
// version checks while large JSON files live only under /data/{version}/json/.
writeFileSync(
  join(DATA, 'meta.json'),
  JSON.stringify({ dataDate, seasonVersion: 9 })
);
copyDeep(publicJsonDir, vJsonDir);
rmSync(join(vJsonDir, 'meta.json'), { force: true });
rmSync(publicJsonDir, { recursive: true, force: true });
mkdirSync(publicJsonDir, { recursive: true });
cpSync(join(DATA, 'meta.json'), join(publicJsonDir, 'meta.json'));

// ---- step 2: build SSR bundle ----
console.log('[ssg] building SSR bundle…');
// Ant Design derives CSS hashes from NODE_ENV, which must match the client build.
execSync(
  'NODE_ENV=production VITE_SSR_BUILD=true node node_modules/.bin/vite build --mode production',
  { cwd: WEB, stdio: 'pipe' }
);

// ---- step 3: load SSR renderer ----
process.env.NODE_ENV = 'production';
const ssrMod = await import(join(SSR_OUT, 'ssr.cjs'));
const render = ssrMod.render || ssrMod.default?.render;

// ---- step 4: read all data ----
console.log('[ssg] reading data files…');
const index = readJSON(join(DATA, 'index.json'));
const moduleData = readJSON(join(DATA, 'dungeon_modules.json'));
const moduleByAlias = new Map();
for (const module of moduleData) {
  for (const alias of [
    module.name,
    ...(module.names ?? []),
    module.sl_base_name,
    ...(module.all_sl_base_names ?? []),
  ]) {
    if (alias) moduleByAlias.set(alias, module);
  }
}

const coordMapNamesCache = new Map();

function readCoordMapNames(ref) {
  if (!ref) return [];
  const cached = coordMapNamesCache.get(ref);
  if (cached) return cached;
  try {
    const value = readJSON(join(DATA, `${ref}.json`));
    const coords = Array.isArray(value) ? value : value.coords || [];
    const mapNames = [
      ...new Set(coords.map((coord) => coord.map).filter(Boolean)),
    ];
    coordMapNamesCache.set(ref, mapNames);
    return mapNames;
  } catch {
    coordMapNamesCache.set(ref, []);
    return [];
  }
}

function templateModuleSummary(module) {
  const imageName = module.img_name || module.sl_base_name;
  if (
    !module.has_img ||
    !imageName ||
    imageName === 'RareModule_1x1' ||
    imageName === 'UnderConstruction_1x1'
  ) {
    return null;
  }
  return {
    name: module.name,
    translation: module.translation,
    translation_key: module.translation_key,
    img_name: module.img_name,
    sl_base_name: module.sl_base_name,
    size_x: module.size_x,
    size_y: module.size_y,
  };
}

function templateModulesFromMapNames(mapNames) {
  const seen = new Set();
  const modules = [];
  for (const mapName of mapNames) {
    const module = moduleByAlias.get(mapName);
    if (!module || seen.has(module.name)) continue;
    const summary = templateModuleSummary(module);
    if (!summary) continue;
    seen.add(module.name);
    modules.push(summary);
  }
  return modules;
}

function templateModulesFromCoords(coords) {
  return templateModulesFromMapNames(
    (coords ?? []).map((coord) => coord.map).filter(Boolean)
  );
}

function lootdropVariantSuffix(item, routeName) {
  if (!item.variants) return null;
  const requested = routeName.match(/_(\d{4})$/)?.[1];
  if (requested && item.variants[requested]) return requested;
  if (item.variants['5001']) return '5001';
  return Object.keys(item.variants).at(-1) ?? null;
}

function templateModulesFromLootdrop(item, routeName) {
  const mapNames = [];
  const suffix = lootdropVariantSuffix(item, routeName);
  if (item.sources && item.variants && suffix) {
    const sourceIds = new Set(
      Object.values(item.variants[suffix]?.group_drop_info ?? {}).flatMap(
        (entries) => entries.map((entry) => entry.source_id)
      )
    );
    for (const sourceId of sourceIds) {
      const source = item.sources[sourceId];
      if (source?.ref) mapNames.push(...readCoordMapNames(source.ref));
    }
  } else {
    for (const monster of item.monsters ?? []) {
      if (monster.coords) {
        mapNames.push(
          ...monster.coords.map((coord) => coord.map).filter(Boolean)
        );
      }
      if (monster.ref) mapNames.push(...readCoordMapNames(monster.ref));
    }
  }
  return templateModulesFromMapNames(mapNames);
}

const PAGES = ['items', 'monsters', 'props', 'lootdrops'];
const DETAIL_TEMPLATE_PAGES = new Set([
  'items',
  'monsters',
  'props',
  'lootdrops',
]);
const SINGLE = ['explore', 'quest_items', 'quest_npc', 'dungeon_modules'];
const DEFAULT_LANG = 'zh-Hans';
const LANGS = [
  'zh-Hans',
  'en',
  'de',
  'es',
  'fr',
  'ja',
  'ko',
  'pt-BR',
  'ru',
  'zh-Hant',
];

// Quest items groups
const questGroups = readJSON(join(DATA, 'quest_items_groups.json'));

// Discover all routes — always generate shell files for detail pages (CSR in quick mode)
const routes = [{ path: '/', file: 'index.html' }];
for (const p of PAGES)
  routes.push({
    path: `/${DEFAULT_LANG}/${p}`,
    file: `${DEFAULT_LANG}/${p}/index.html`,
  });
for (const p of SINGLE)
  routes.push({
    path: `/${DEFAULT_LANG}/${p}`,
    file: `${DEFAULT_LANG}/${p}/index.html`,
  });
for (const g of questGroups) {
  routes.push({
    path: `/${DEFAULT_LANG}/quest_items/${g.group}`,
    file: `${DEFAULT_LANG}/quest_items/${g.group}/index.html`,
  });
}

// Dungeon modules: group pages and module detail pages
const dmGroups = new Set(moduleData.map((m) => m.group).filter(Boolean));
for (const g of dmGroups) {
  routes.push({
    path: `/${DEFAULT_LANG}/dungeon_modules/${g}`,
    file: `${DEFAULT_LANG}/dungeon_modules/${g}/index.html`,
  });
}
for (const m of moduleData) {
  const group = m.group || '';
  routes.push({
    path: `/${DEFAULT_LANG}/dungeon_modules/${group}/${m.name}`,
    file: `${DEFAULT_LANG}/dungeon_modules/${group}/${m.name}/index.html`,
  });
}

for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    const availableSuffixes = e.variant_suffixes ?? [];
    const unavailableSuffixes = e.unavailable_variant_suffixes ?? [];
    const routeSuffixes = [...availableSuffixes, ...unavailableSuffixes];
    if (p === 'lootdrops' && routeSuffixes.length > 1) {
      // Base lootdrop entry (e.g. "HeaterShield") redirects to default variant;
      // generate a minimal redirect page, then create per-suffix variant pages.
      const defaultSuffix = availableSuffixes.includes('5001')
        ? '5001'
        : availableSuffixes[availableSuffixes.length - 1];
      const target = `/${DEFAULT_LANG}/lootdrops/${e.name}_${defaultSuffix}/`;
      routes.push({
        path: `/${DEFAULT_LANG}/${p}/${encodeURIComponent(e.name)}`,
        file: `${DEFAULT_LANG}/${p}/${e.name}/index.html`,
        redirect: target,
      });
      for (const suffix of routeSuffixes) {
        const variantName = `${e.name}_${suffix}`;
        routes.push({
          path: `/${DEFAULT_LANG}/lootdrops/${encodeURIComponent(variantName)}`,
          file: `${DEFAULT_LANG}/lootdrops/${variantName}/index.html`,
        });
      }
    } else {
      routes.push({
        path: `/${DEFAULT_LANG}/${p}/${encodeURIComponent(e.name)}`,
        file: `${DEFAULT_LANG}/${p}/${e.name}/index.html`,
      });
    }
  }
}

// Quest NPC detail pages
const questNpcData = readJSON(join(DATA, 'quest_npc.json'));
for (const npc of questNpcData) {
  routes.push({
    path: `/${DEFAULT_LANG}/quest_npc/${encodeURIComponent(npc.npc_name)}`,
    file: `${DEFAULT_LANG}/quest_npc/${npc.npc_name}/index.html`,
  });
}

// Build per-route data lookup
const ssrDataMap = {};

// Homepage
ssrDataMap['home'] = index;

// List pages — use search_index.json as single source of truth
const searchIndex = readJSON(join(DATA, 'search_index.json'));
for (const p of PAGES) {
  ssrDataMap[`list-${p}`] = searchIndex.filter((e) => e.page === p);
}
for (const p of SINGLE) {
  if (p === 'dungeon_modules') {
    const groupOrder = [
      'GoblinCave',
      'FireDeep',
      'IceCavern',
      'IceAbyss',
      'Ruins',
      'Crypt',
      'Inferno',
      'ShipGraveyard',
    ];
    const groupMap = new Map();
    for (const m of moduleData) {
      const g = m.group || '';
      if (!groupMap.has(g)) {
        groupMap.set(g, {
          group: g,
          group_key: m.group_key,
          group_floor: m.group_floor,
          group_sub_key: m.group_sub_key,
          group_display: m.group_display || g || '未分组',
          module_count: 0,
        });
      }
      groupMap.get(g).module_count++;
    }
    ssrDataMap['dungeon_modules'] = [...groupMap.values()].sort(
      (a, b) => groupOrder.indexOf(a.group) - groupOrder.indexOf(b.group)
    );
    continue;
  }
  // quest_items: pipeline-internal file, use quest_items_groups.json instead
  if (p === 'quest_items') {
    ssrDataMap[p] = readJSON(join(DATA, 'quest_items_groups.json'));
    continue;
  }
  ssrDataMap[p] = readJSON(join(DATA, `${p}.json`));
}

// Quest items group detail pages
for (const g of questGroups) {
  if (!QUICK) {
    try {
      const qg = readJSON(join(DATA, 'quest_items_groups', `${g.group}.json`));
      ssrDataMap[`quest_items_groups/${g.group}`] = qg;
    } catch {}
  } else {
    ssrDataMap[`quest_items_groups/${g.group}`] = {
      group: g.group,
      group_key: g.group_key,
      group_floor: g.group_floor,
      group_sub_key: g.group_sub_key,
      group_display: g.group_display,
      entity_count: g.entity_count,
      position_count: g.position_count,
      entities: [],
    };
  }
}

// Dungeon modules group pages
for (const g of dmGroups) {
  const groupMods = moduleData.filter((m) => m.group === g);
  ssrDataMap[`dungeon_modules/${g}`] = groupMods;
}
// Dungeon modules module data is available globally for detail pages

// Explore page needs module data too
ssrDataMap['explore-modules'] = moduleData;
ssrDataMap['explore'] = readJSON(join(DATA, 'explore.json'));

// Detail pages — full SSR data (full mode) or minimal SSR data (quick mode)
for (const p of PAGES) {
  const list = readJSON(join(DATA, `${p}.json`));
  for (const e of list) {
    const name = e.name;
    const routeSuffixes = [
      ...(e.variant_suffixes ?? []),
      ...(e.unavailable_variant_suffixes ?? []),
    ];
    const detailFilePath =
      p === 'lootdrops'
        ? join(DATA, 'lootdrops', `${name}.json`)
        : join(DATA, p, `${name}.json`);
    let detailData;
    try {
      detailData = readJSON(detailFilePath);
    } catch {
      detailData = null;
    }
    if (!QUICK) {
      try {
        if (!detailData) throw new Error('detail data not found');
        if (p === 'lootdrops') {
          const itemData = {
            item: detailData,
            modules: moduleData,
            templateModules: templateModulesFromLootdrop(detailData, name),
          };
          ssrDataMap[`lootdrops/${name}`] = itemData;
          // Variant routes select from the same merged base detail in memory.
          if (routeSuffixes.length > 1) {
            for (const suffix of routeSuffixes) {
              ssrDataMap[`lootdrops/${name}_${suffix}`] = {
                item: itemData.item,
                modules: moduleData,
                templateModules: templateModulesFromLootdrop(
                  detailData,
                  `${name}_${suffix}`
                ),
              };
            }
          }
        } else {
          ssrDataMap[`${p}/${name}`] = {
            entity: detailData,
            modules: moduleData,
            templateModules: templateModulesFromCoords(detailData.coords),
          };
        }
      } catch {
        // skip — no individual data file for this entry
      }
    } else {
      // Quick mode: inject minimal metadata for SEO (name + translation only)
      if (p === 'lootdrops') {
        const minimalItem = {
          item: {
            name: e.name,
            translation: e.translation,
            translation_key: e.translation_key,
          },
        };
        ssrDataMap[`lootdrops/${name}`] = {
          ...minimalItem,
          templateModules: detailData
            ? templateModulesFromLootdrop(detailData, name)
            : [],
        };
        if (routeSuffixes.length > 1) {
          for (const suffix of routeSuffixes) {
            ssrDataMap[`lootdrops/${name}_${suffix}`] = {
              ...minimalItem,
              templateModules: detailData
                ? templateModulesFromLootdrop(detailData, `${name}_${suffix}`)
                : [],
            };
          }
        }
      } else {
        ssrDataMap[`${p}/${name}`] = {
          entity: {
            name: e.name,
            translation: e.translation,
            translation_key: e.translation_key,
          },
          templateModules: detailData
            ? templateModulesFromCoords(detailData.coords)
            : [],
        };
      }
    }
  }
}

// Dungeon module detail pages — SSR data injection (coords + module info)
for (const m of moduleData) {
  const group = m.group || '';
  const key = `dungeon_modules_detail/${group}/${m.name}`;
  if (!QUICK) {
    try {
      const coordsFile = join(DATA, 'dungeon_modules_coords', `${m.name}.json`);
      const coords = readJSON(coordsFile);
      ssrDataMap[key] = { module: m, coords };
    } catch {
      ssrDataMap[key] = { module: m, coords: null };
    }
  } else {
    ssrDataMap[key] = {
      module: m,
      coords: null,
    };
  }
}

// ---- step 4b: P005 — preload referenced entity coords for lootdrop detail pages ----
if (!QUICK) {
  console.log('[ssg] preloading referenced coords for lootdrop detail pages…');
  let refCount = 0;
  for (const [key, data] of Object.entries(ssrDataMap)) {
    if (!key.startsWith('lootdrops/')) continue;
    const item = data.item;
    if (!item?.monsters && !item?.sources) continue;

    const refCoordsMap = {};
    let refs =
      item.monsters?.map((monster) => monster.ref).filter(Boolean) ?? [];
    if (item.sources && item.variants) {
      const routeName = key.slice('lootdrops/'.length);
      const suffixMatch = routeName.match(/_(\d{4})$/);
      const suffix =
        suffixMatch && suffixMatch[1] !== '8001'
          ? suffixMatch[1]
          : Object.keys(item.variants).includes('5001')
            ? '5001'
            : Object.keys(item.variants)[0];
      const sourceIds = new Set(
        Object.values(item.variants[suffix]?.group_drop_info ?? {}).flatMap(
          (entries) => entries.map((entry) => entry.source_id)
        )
      );
      refs = [...sourceIds]
        .map((sourceId) => item.sources[sourceId]?.ref)
        .filter(Boolean);
    }
    for (const ref of new Set(refs)) {
      const refFile = join(DATA, `${ref}.json`);
      try {
        const refEntity = readJSON(refFile);
        refCoordsMap[ref] = Array.isArray(refEntity)
          ? refEntity
          : refEntity.coords || [];
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
const template = readFileSync(join(DIST, 'index.html'), 'utf-8');
console.log(`[ssg] rendering ${routes.length} routes…`);

const t0 = Date.now();
console.log(`[ssg] mode=${QUICK ? 'quick' : 'full'} — ${routes.length} routes`);
const ROOT_MARKER = '<div id="root">';
const HEAD_CLOSE = '</head>';
const DESCRIPTION_META_RE =
  /\s*<meta\s+name=["']description["']\s+content=["'][^"']*["']\s*\/?\s*>/i;
const SSR_SCRIPT_RE = /<script>window\.__SSR_DATA__=(.*?)<\/script>/s;
function isTemplateDetailRoute(path) {
  const match = path.match(/^\/(?:[^/]+\/)?([^/]+)\/[^/]+$/);
  if (match && DETAIL_TEMPLATE_PAGES.has(match[1])) return true;
  return /^\/(?:[^/]+\/)?dungeon_modules\/[^/]+\/[^/]+$/.test(path);
}

/**
 * Map route path to its data key in ssrDataMap.
 */
function routeDataKey(path) {
  if (path === '/') return 'home';
  // Strip default language prefix for route matching
  const langPrefix = `/${DEFAULT_LANG}`;
  const stripped = path.startsWith(langPrefix)
    ? path.slice(langPrefix.length) || '/'
    : path;
  if (
    stripped.startsWith('/items/') ||
    stripped.startsWith('/monsters/') ||
    stripped.startsWith('/props/')
  )
    return stripped.slice(1);
  if (stripped.startsWith('/lootdrops/')) {
    return `lootdrops/${decodeURIComponent(stripped.slice('/lootdrops/'.length))}`;
  }
  if (stripped.startsWith('/quest_items/'))
    return `quest_items_groups/${stripped.split('/')[2]}`;
  if (stripped === '/quest_items') return 'quest_items';
  if (stripped === '/quest_npc') return 'quest_npc';
  if (stripped.startsWith('/quest_npc/')) return 'quest_npc';
  if (stripped === '/dungeon_modules') return 'dungeon_modules';
  if (stripped.startsWith('/dungeon_modules/')) {
    const parts = stripped.split('/');
    if (parts.length === 3) return `dungeon_modules/${parts[2]}`;
    if (parts.length >= 4)
      return `dungeon_modules_detail/${parts[2]}/${parts[3]}`;
    return '';
  }
  if (stripped === '/explore') return 'explore';
  return `list-${stripped.slice(1)}`;
}

/**
 * Compute <base href="..."> value from output file path relative to dist root.
 */
function baseHrefFromFile(_file) {
  return BASE;
}

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function localizedPath(path, lang) {
  // Strip any existing language prefix
  const parts = path.split('/').filter(Boolean);
  if (parts.length > 0 && LANGS.includes(parts[0])) {
    path = '/' + parts.slice(1).join('/') || '/';
  }
  const canonical = path === '/' ? '/' : path.replace(/\/?$/, '/');
  const rel = `/${lang}${canonical}`;
  return BASE === '/' ? rel : BASE.replace(/\/$/, '') + rel;
}

function alternateLinks(path) {
  return LANGS.map((lang) => {
    const href = SITE + localizedPath(path, lang);
    return `<link rel="alternate" hreflang="${lang}" href="${href}">`;
  }).join('\n    ');
}

function firstTranslatable(data) {
  if (!data || typeof data !== 'object') return null;
  if (data.translation_key || data.translation) return data;
  if (data.entity) return firstTranslatable(data.entity);
  if (data.item) return firstTranslatable(data.item);
  if (data.module) return firstTranslatable(data.module);
  if (Array.isArray(data)) return null;
  return null;
}

function stripTrailingParenthetical(value) {
  return String(value ?? '')
    .replace(/\s*[（(][^（）()]*[）)]\s*$/, '')
    .trim();
}

function localizedTitle(
  routeData,
  localeDict,
  routePath = '',
  lang = DEFAULT_LANG
) {
  if (routePath === '/') {
    return (
      HOME_TITLE_DESCRIPTIONS[lang] || HOME_TITLE_DESCRIPTIONS[DEFAULT_LANG]
    );
  }
  const entity = firstTranslatable(routeData);
  if (!entity) return '';
  const title = entity.translation_key
    ? localeDict[entity.translation_key]
    : '';
  const localized =
    title || entity.translation || entity.name || 'DarkFlashNav';
  const lootdropVariant = routePath.match(/\/lootdrops\/[^/]+_(\d{4})\/?$/);
  return lootdropVariant && lootdropVariant[1] !== '8001'
    ? stripTrailingParenthetical(localized)
    : localized;
}

function decodeHtml(value) {
  return value
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function localizedDocumentTitle(route, routeData, localeDict, lang) {
  // Detail shells deliberately avoid rendering full route data. Their concise
  // entity title remains available from the route metadata.
  if (isTemplateDetailRoute(route.path)) {
    return `${localizedTitle(routeData, localeDict, route.path, lang)} | 越来越黑暗闪电指南 DarkFlashNav`;
  }
  try {
    const result = render(localizedPath(route.path, lang), {
      ...ssrDataMap,
      __locale: localeDict,
    });
    const match = result.head.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    if (match) return decodeHtml(match[1]);
  } catch (err) {
    console.error(`  [title] ${route.path} (${lang}): ${err.message}`);
  }
  const entityTitle = localizedTitle(routeData, localeDict, route.path, lang);
  return entityTitle ? `${entityTitle} | 越来越黑暗闪电指南 DarkFlashNav` : '';
}

function injectLocalizedData(
  page,
  lang,
  title,
  description,
  ssrLang = DEFAULT_LANG,
  localeDict
) {
  const inject = (jsonText = '{}') => {
    try {
      const payload = JSON.parse(jsonText);
      payload.__lang = lang;
      payload.__ssrLang = ssrLang;
      if (localeDict) payload.__locale = localeDict;
      if (title) payload.__localizedTitle = title;
      payload.__localizedDescription = description;
      return `<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>`;
    } catch {
      return '';
    }
  };
  if (SSR_SCRIPT_RE.test(page)) {
    return page.replace(SSR_SCRIPT_RE, (_match, jsonText) => inject(jsonText));
  }
  return page.replace(HEAD_CLOSE, `${inject()}\n${HEAD_CLOSE}`);
}

function replaceDescriptionMeta(page, description) {
  const descriptionMeta = `<meta data-rh="true" name="description" content="${escapeHtml(description)}">`;
  const ogDescriptionMeta = `<meta data-rh="true" property="og:description" content="${escapeHtml(description)}">`;
  const withoutDescriptions = page
    .replace(/<meta\b(?=[^>]*\bname="description")[^>]*>/gi, '')
    .replace(/<meta\b(?=[^>]*\bproperty="og:description")[^>]*>/gi, '');
  return withoutDescriptions.replace(
    HEAD_CLOSE,
    `${descriptionMeta}\n${ogDescriptionMeta}\n${HEAD_CLOSE}`
  );
}

function templateDescription(route, routeData, localeDict, lang) {
  const parts = route.path.split('/').filter(Boolean);
  if (parts[0] === DEFAULT_LANG) parts.shift();
  const [section] = parts;
  const name = localizedTitle(routeData, localeDict, route.path, lang);
  if (section === 'lootdrops') {
    return buildSeoDescription(lang, 'lootdrop', { name });
  }
  if (section === 'dungeon_modules') {
    const module = routeData?.module;
    return buildSeoDescription(lang, 'module', {
      name,
      width: module?.size_x || undefined,
      height: module?.size_y || undefined,
    });
  }
  return buildSeoDescription(lang, 'entity', { name });
}

function pageDescription(page, route, routeData, localeDict, lang) {
  if (isTemplateDetailRoute(route.path)) {
    return templateDescription(route, routeData, localeDict, lang);
  }
  const match = page.match(
    /<meta\b(?=[^>]*\bname="description")(?=[^>]*\bcontent="([^"]*)")[^>]*>/i
  );
  return match ? decodeHtml(match[1]) : buildSeoDescription(lang, 'home');
}

function localizePage(
  page,
  route,
  routeData,
  localeDict,
  lang,
  includeAlternates = true,
  ssrLang = DEFAULT_LANG,
  ssrLocaleDict
) {
  const canonicalHref = localizedPath(route.path, lang);
  const title = localizedDocumentTitle(route, routeData, localeDict, lang);
  const description = pageDescription(page, route, routeData, localeDict, lang);
  let out = replaceDescriptionMeta(
    injectLocalizedData(page, lang, title, description, ssrLang, ssrLocaleDict),
    description
  )
    .replace(/<html(\s[^>]*)?>/, `<html lang="${lang}">`)
    .replace(
      /<link rel="canonical" href="[^"]*">/,
      `<link rel="canonical" href="${canonicalHref}">`
    );
  if (includeAlternates) {
    out = out.replace(
      HEAD_CLOSE,
      `    ${alternateLinks(route.path)}\n${HEAD_CLOSE}`
    );
  }
  if (title) {
    const titleTag = `<title>${escapeHtml(title)}</title>`;
    out = /<title[^>]*>[^<]*<\/title>/.test(out)
      ? out.replace(/<title[^>]*>[^<]*<\/title>/, titleTag)
      : out.replace(HEAD_CLOSE, `    ${titleTag}\n${HEAD_CLOSE}`);
  }
  return out;
}

function renderLocalizedPage(route, lang, localeDict) {
  const urlPath = localizedPath(route.path, lang);
  const dataKey = routeDataKey(route.path);
  const routeData = ssrDataMap[dataKey];
  const canonical = urlPath.replace(/\/?$/, '/');
  const templated = template.replace(
    '</title>',
    `</title>\n    <link rel="canonical" href="${canonical}">\n    <base href="${baseHrefFromFile(route.file)}">`
  );
  const payload = { [dataKey]: routeData };
  const result = render(urlPath, { ...ssrDataMap, __locale: localeDict });
  const page = templated
    .replace(/<title>[^<]*<\/title>\s*/, '')
    .replace(DESCRIPTION_META_RE, '')
    .replace(ROOT_MARKER, `<div id="root">${result.html}`)
    .replace(
      HEAD_CLOSE,
      `${result.head}\n<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`
    );
  return page;
}

function detailPreloads(urlPath) {
  const detailMatch = urlPath.match(
    /^\/(?:[^/]+\/)?(items|monsters|props|lootdrops)\/(.+)$/
  );
  if (detailMatch) {
    let detailName = detailMatch[2];
    if (detailMatch[1] === 'lootdrops') {
      detailName = lootdropBaseName(detailName);
    }
    return `    <link rel="preload" href="/data/${shortVer}/json/${detailMatch[1]}/${detailName}.json" as="fetch" crossorigin="anonymous">\n`;
  }
  const moduleMatch = urlPath.match(
    /^\/(?:[^/]+\/)?dungeon_modules\/[^/]+\/(.+)$/
  );
  if (!moduleMatch) return '';
  return `    <link rel="preload" href="/data/${shortVer}/json/dungeon_modules_coords/${moduleMatch[1]}.json" as="fetch" crossorigin="anonymous">\n`;
}

function lootdropBaseName(name) {
  const match = name.match(/^(.+)_(\d{4})$/);
  return match && match[2] !== '8001' ? match[1] : name;
}

function localizedTemplateModuleName(module, localeDict) {
  return (
    (module.translation_key && localeDict?.[module.translation_key]) ||
    module.translation ||
    module.name
  );
}

const TEMPLATE_MODULE_HEADINGS = {
  'zh-Hans': '地图模块表',
  en: 'Dungeon map modules',
  de: 'Dungeon-Module',
  es: 'Módulos de mazmorra',
  fr: 'Modules de donjon',
  ja: 'ダンジョンモジュール',
  ko: '던전 모듈',
  'pt-BR': 'Módulos de masmorra',
  ru: 'Модули подземелья',
  'zh-Hant': '地圖模組表',
};

function detailPlaceholder(title, modules, localeDict, lang) {
  const moduleHeading = TEMPLATE_MODULE_HEADINGS[lang] || '地图模块表';
  const moduleCards = modules
    .map((module) => {
      const name = localizedTemplateModuleName(module, localeDict);
      const imageName = module.img_name || module.sl_base_name;
      const sx = Number(module.size_x) || 1;
      const sy = Number(module.size_y) || 1;
      const imageUrl = `/data/img/${imageName}.webp`;
      return `<article style="min-width:0;border:1px solid #434343;border-radius:5px;padding:8px;background:#1f1f1f">
  <h3 style="margin:0 0 6px;text-align:center;font-size:18px;line-height:1.3;color:#ffc107">${escapeHtml(name)}</h3>
  <div style="aspect-ratio:${sx} / ${sy};overflow:hidden;border-radius:3px;background:#141414">
    <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(name)}" loading="lazy" decoding="async" style="display:block;width:100%;height:100%;object-fit:cover">
  </div>
</article>`;
    })
    .join('\n');
  const content = moduleCards
    ? `<h2 style="margin:0 0 10px;font-size:22px;color:#ffc107">${escapeHtml(moduleHeading)}</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px">${moduleCards}</div>`
    : `<p>未找到可显示的地图模块。</p>`;
  return `<main aria-busy="false" style="max-width:1200px;min-height:100vh;margin:0 auto;padding:16px;box-sizing:border-box;background:#141414;color:#f5f5f5">
  <h1 style="margin:0 0 16px;text-align:center;color:#ffc107;font-size:32px">${escapeHtml(title)}</h1>
  <section aria-label="${escapeHtml(moduleHeading)}" style="color:#f5f5f5">
    ${content}
  </section>
</main>`;
}

function detailTemplate() {
  return template
    .replace(/\s*<style>[\s\S]*?<\/style>/, '')
    .replace(
      /\s*<link rel="preload" href="\/data\/(?:json\/meta\.json|[^"/]+\/json\/(?:dungeon_modules|index|search_index)\.json)" as="fetch" crossorigin="anonymous">/g,
      ''
    );
}

function createTemplateDetailPage(route, routeData, lang, localeDict) {
  const urlPath = route.path;
  const canonical = urlPath === '/' ? '/' : urlPath.replace(/\/?$/, '/');
  const templated = detailTemplate().replace(
    '</title>',
    `</title>\n    <link rel="canonical" href="${canonical}">\n    <base href="${baseHrefFromFile(route.file)}">`
  );
  // Detail pages fetch their route data after the client starts. Keep the static
  // shell limited to module summaries instead of rendering coordinates and styles.
  const title = localizedTitle(routeData, localeDict, route.path);
  const modules = routeData?.templateModules ?? [];
  const page = templated
    .replace(/<title>[^<]*<\/title>\s*/, '')
    .replace(
      ROOT_MARKER,
      `<div id="root" data-detail-placeholder>${detailPlaceholder(title, modules, localeDict, lang)}`
    )
    .replace(HEAD_CLOSE, `${detailPreloads(urlPath)}</head>`);
  return page;
}

for (let i = 0; i < routes.length; i++) {
  const r = routes[i];
  if (r.generateStatic === false) continue;
  const outPath = join(DIST, r.file);
  const urlPath = r.path;
  const baseHref = baseHrefFromFile(r.file);
  const dataKey = routeDataKey(urlPath);
  const routeData = ssrDataMap[dataKey];

  // Base tag must be first in <head> so script/link assets resolve correctly.
  // Canonical URL with trailing slash for SEO
  const canonical = urlPath === '/' ? '/' : urlPath.replace(/\/?$/, '/');
  const templated = template.replace(
    '</title>',
    `</title>\n    <link rel="canonical" href="${canonical}">\n    <base href="${baseHref}">`
  );

  // Detail-specific preload links (versioned paths)
  const detailPreloads = [];
  const entityMatch = urlPath.match(
    /^\/(?:[^/]+\/)?(items|monsters|props)\/(.+)$/
  );
  if (entityMatch) {
    detailPreloads.push(
      `<link rel="preload" href="/data/${shortVer}/json/${entityMatch[1]}/${entityMatch[2]}.json" as="fetch" crossorigin="anonymous">`
    );
  }
  const lootdropMatch = urlPath.match(/^\/(?:[^/]+\/)?lootdrops\/(.+)$/);
  if (lootdropMatch) {
    detailPreloads.push(
      `<link rel="preload" href="/data/${shortVer}/json/lootdrops/${lootdropBaseName(lootdropMatch[1])}.json" as="fetch" crossorigin="anonymous">`
    );
  }
  const moduleMatch = urlPath.match(
    /^\/(?:[^/]+\/)?dungeon_modules\/[^/]+\/(.+)$/
  );
  if (moduleMatch) {
    detailPreloads.push(
      `<link rel="preload" href="/data/${shortVer}/json/dungeon_modules_coords/${moduleMatch[1]}.json" as="fetch" crossorigin="anonymous">`,
      `<link rel="preload" href="/data/img/${moduleMatch[1]}.webp" as="fetch" crossorigin="anonymous">`
    );
  }
  const preloadHtml =
    detailPreloads.length > 0 ? `    ${detailPreloads.join('\n    ')}\n` : '';

  let page;
  if (r.redirect) {
    const title = `${r.file.split('/')[1]} | 越来越黑暗闪电指南 DarkFlashNav`;
    page = `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>${title}</title>
<link rel="canonical" href="${r.redirect}">
<meta http-equiv="refresh" content="0;url=${r.redirect}"></head>
<body><script>window.location.replace("${r.redirect}");</script></body>
</html>`;
  } else if (isTemplateDetailRoute(urlPath)) {
    page = createTemplateDetailPage(r, routeData, DEFAULT_LANG, {});
  } else if (routeData) {
    const payload = { [dataKey]: routeData };
    try {
      const result = render(urlPath, ssrDataMap);
      const headlessTemplate = templated
        .replace(/<title>[^<]*<\/title>\s*/, '')
        .replace(DESCRIPTION_META_RE, '');
      page = headlessTemplate
        .replace(ROOT_MARKER, `<div id="root">${result.html}`)
        .replace(
          HEAD_CLOSE,
          `${preloadHtml}${result.head}\n<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`
        );
    } catch (err) {
      console.error(`  [err]  ${urlPath}: ${err.message}`);
      page = templated.replace(
        HEAD_CLOSE,
        `${preloadHtml}<script>window.__SSR_DATA__=${JSON.stringify(payload)}</script>\n</head>`
      );
    }
  } else {
    page = templated.replace(HEAD_CLOSE, `${preloadHtml}\n</head>`);
  }
  if (!r.redirect) {
    page = replaceDescriptionMeta(
      page,
      pageDescription(page, r, routeData, {}, DEFAULT_LANG)
    );
  }

  if (urlPath === '/' && !/<title[^>]*>[^<]*<\/title>/.test(page)) {
    page = page.replace(
      HEAD_CLOSE,
      `    <title>越来越黑暗闪电指南 DarkFlashNav | ${HOME_TITLE_DESCRIPTIONS[DEFAULT_LANG]}</title>\n${HEAD_CLOSE}`
    );
  }

  if (!r.redirect) {
    page = localizePage(page, r, routeData, {}, DEFAULT_LANG, false);
  }

  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, page, 'utf-8');

  if ((i + 1) % 100 === 0 || i === routes.length - 1) {
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`  [${i + 1}/${routes.length}] ${elapsed}s`);
  }
}

// ---- step 5b: generate localized HTML copies ----
console.log(
  `[ssg] generating localized HTML copies for ${LANGS.filter((l) => l !== DEFAULT_LANG).length} non-default languages…`
);
const localeDicts = { [DEFAULT_LANG]: {} };
for (const lang of LANGS) {
  if (lang === DEFAULT_LANG) continue;
  localeDicts[lang] = readJSON(join(DATA, 'locale', `${lang}.json`));
}
let localizedCount = 0;
for (const lang of LANGS) {
  for (const r of routes) {
    if (lang === DEFAULT_LANG && r.path !== '/') continue;
    if (r.redirect) continue;
    if (r.generateStatic === false) continue;
    const dataKey = routeDataKey(r.path);
    const routeData = ssrDataMap[dataKey];
    // Strip DEFAULT_LANG prefix from file path for target lang directory
    const langFilePrefix = `${DEFAULT_LANG}/`;
    const relFile = r.file.startsWith(langFilePrefix)
      ? r.file.slice(langFilePrefix.length)
      : r.file;
    const dstFile =
      relFile === 'index.html' ? `${lang}/index.html` : join(lang, relFile);
    const dstPath = join(DIST, dstFile);
    const usesTemplateDetail = isTemplateDetailRoute(r.path);
    const basePage = usesTemplateDetail
      ? createTemplateDetailPage(r, routeData, lang, localeDicts[lang])
      : renderLocalizedPage(r, lang, localeDicts[lang]);
    const page = localizePage(
      basePage,
      r,
      routeData,
      localeDicts[lang],
      lang,
      true,
      usesTemplateDetail ? DEFAULT_LANG : lang,
      usesTemplateDetail ? undefined : localeDicts[lang]
    );
    mkdirSync(dirname(dstPath), { recursive: true });
    writeFileSync(dstPath, page, 'utf-8');
    localizedCount++;
  }
}
console.log(`[ssg] localized HTML generated: ${localizedCount}`);

// ---- step 5c: preserve legacy URLs with static default-language redirects ----
let legacyRedirectCount = 0;
for (const r of routes) {
  if (r.path === '/' || r.generateStatic === false) continue;
  const legacyFile = r.file.replace(new RegExp(`^${DEFAULT_LANG}/`), '');
  const target = r.redirect || `${r.path.replace(/\/?$/, '/')}`;
  const redirectPage = `<!doctype html>
<html lang="${DEFAULT_LANG}">
<head>
  <meta charset="utf-8">
  <link rel="canonical" href="${target}">
  <meta http-equiv="refresh" content="0;url=${target}">
  <script>window.location.replace(${JSON.stringify(target)} + window.location.search + window.location.hash);</script>
</head>
<body></body>
</html>`;
  const legacyPath = join(DIST, legacyFile);
  mkdirSync(dirname(legacyPath), { recursive: true });
  writeFileSync(legacyPath, redirectPage, 'utf-8');
  legacyRedirectCount++;
}
console.log(`[ssg] legacy redirects generated: ${legacyRedirectCount}`);

// ---- step 6: 404.html ----
writeFileSync(join(DIST, '404.html'), template, 'utf-8');

// ---- step 7: cleanup SSR bundle and manifest ----
rmSync(SSR_OUT, { recursive: true, force: true });
try {
  rmSync(join(DIST, '.vite'), { recursive: true, force: true });
} catch {}
console.log('[ssg] SSR build cleaned up');

// ---- step 8: sitemap.xml ----
const dataDateStr = new Date(Number(dataDate) * 1000)
  .toISOString()
  .split('T')[0];

function sitemapPriority(path) {
  if (path === '/') return ['1.0', 'daily'];
  if (path === '/explore') return ['0.7', 'weekly'];
  if (
    path.startsWith('/items/') ||
    path.startsWith('/monsters/') ||
    path.startsWith('/props/')
  )
    return ['0.6', 'weekly'];
  if (path.startsWith('/lootdrops/')) return ['0.5', 'weekly'];
  if (path.startsWith('/dungeon_modules/')) return ['0.5', 'weekly'];
  if (path.startsWith('/quest_')) return ['0.4', 'monthly'];
  // list pages
  if (path.split('/').length <= 2) return ['0.8', 'weekly'];
  return ['0.3', 'monthly'];
}

const sitemapFiles = [];
const sitemapEntries = new Map();
const SITEMAP_HEADER =
  '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n';
const SITEMAP_FOOTER = '</urlset>\n';
const SITEMAP_MAX_BYTES = 25 * 1024 * 1024;
const SITEMAP_MAX_URLS = 50_000;
const SITEMAP_DETACH_ORDER = [
  'ru',
  'pt-BR',
  'ko',
  'ja',
  'de',
  'fr',
  'es',
  'zh-Hant',
];
for (const lang of LANGS) {
  let entries = '';
  for (const r of routes) {
    if (r.redirect) continue;
    if (r.generateStatic === false) continue;
    const [prio, freq] = sitemapPriority(r.path);
    const loc = SITE + localizedPath(r.path, lang);
    const alts = LANGS.map(
      (altLang) =>
        `    <xhtml:link rel="alternate" hreflang="${altLang}" href="${SITE + localizedPath(r.path, altLang)}" />`
    ).join('\n');
    entries += `  <url>\n    <loc>${loc}</loc>\n${alts}\n    <lastmod>${dataDateStr}</lastmod>\n    <changefreq>${freq}</changefreq>\n    <priority>${prio}</priority>\n  </url>\n`;
  }
  const sitemap = `${SITEMAP_HEADER}${entries}${SITEMAP_FOOTER}`;
  const filename = `sitemap-${lang}.xml`;
  writeFileSync(join(DIST, filename), sitemap, 'utf-8');
  sitemapFiles.push(filename);
  sitemapEntries.set(lang, entries);
}

function buildCombinedSitemap(langs) {
  return `${SITEMAP_HEADER}${langs.map((lang) => sitemapEntries.get(lang)).join('')}${SITEMAP_FOOTER}`;
}

function countSitemapUrls(langs) {
  return langs.reduce(
    (count, lang) =>
      count + (sitemapEntries.get(lang)?.match(/<url>/g) ?? []).length,
    0
  );
}

const rootSitemapLanguages = [...LANGS];
const detachedSitemapLanguages = [];
let combinedSitemap = buildCombinedSitemap(rootSitemapLanguages);
while (
  (Buffer.byteLength(combinedSitemap, 'utf8') > SITEMAP_MAX_BYTES ||
    countSitemapUrls(rootSitemapLanguages) > SITEMAP_MAX_URLS) &&
  rootSitemapLanguages.length > 1
) {
  const lang =
    SITEMAP_DETACH_ORDER.find((candidate) =>
      rootSitemapLanguages.includes(candidate)
    ) || rootSitemapLanguages[rootSitemapLanguages.length - 1];
  rootSitemapLanguages.splice(rootSitemapLanguages.indexOf(lang), 1);
  detachedSitemapLanguages.push(lang);
  combinedSitemap = buildCombinedSitemap(rootSitemapLanguages);
}

writeFileSync(join(DIST, 'sitemap.xml'), combinedSitemap, 'utf-8');
console.log(
  `[ssg] sitemap.xml combined ${rootSitemapLanguages.join(',')} (${Buffer.byteLength(combinedSitemap, 'utf8')} bytes, ${countSitemapUrls(rootSitemapLanguages)} URLs)`
);
if (detachedSitemapLanguages.length > 0) {
  console.log(
    `[ssg] detached language sitemaps: ${detachedSitemapLanguages.join(', ')}`
  );
}
console.log(
  `[ssg] ${sitemapFiles.length} language sitemap files generated (${routes.length - routes.filter((r) => r.redirect).length} URLs per language)`
);

function countDistFiles(dir) {
  let files = 0;
  let html = 0;
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      const nested = countDistFiles(path);
      files += nested.files;
      html += nested.html;
    } else {
      files++;
      if (name.endsWith('.html')) html++;
    }
  }
  return { files, html };
}

const distCounts = countDistFiles(DIST);
console.log(
  `[ssg] dist files: ${distCounts.files} (${distCounts.html} HTML, limit 19000)`
);
if (distCounts.files > 19000) {
  throw new Error(
    `[ssg] dist file budget exceeded: ${distCounts.files} > 19000. Reassess the generated route set before deployment.`
  );
}

const total = ((Date.now() - t0) / 1000).toFixed(1);
console.log(
  `[ssg] done! ${routes.length} pages in ${total}s (mode=${QUICK ? 'quick' : 'full'})`
);
