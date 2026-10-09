import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.env.BASE_URL || 'http://localhost:8080';
const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../..'
);
const TIMEOUT = 20000;
const EXPECTED_PLACEHOLDER = {
  'zh-Hans': '搜索物品/怪物/实体...',
  en: 'Search items/monsters/props...',
  de: 'Gegenstände/Monster/Objekte suchen...',
  es: 'Buscar objetos/monstruos...',
  fr: 'Rechercher objets/monstres...',
  ja: 'アイテム/モンスターを検索...',
  ko: '아이템/몬스터 검색...',
  'pt-BR': 'Buscar itens/monstros...',
  ru: 'Поиск предметов/монстров...',
  'zh-Hant': '搜尋物品/怪物/實體...',
};

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
const HOME_PAGES = LANGS.map((lang) => ({
  path: `/${lang}/`,
  desc: `HomePage(${lang})`,
  lang,
}));

const PAGES = [
  ...HOME_PAGES,
  { path: '/zh-Hans/items/', desc: 'ItemsList', lang: 'zh-Hans' },
  { path: '/en/items/', desc: 'ItemsList(en)', lang: 'en' },
  { path: '/ja/items/', desc: 'ItemsList(ja)', lang: 'ja' },
  { path: '/zh-Hans/items/Ale/', desc: 'ItemDetail(Ale)', lang: 'zh-Hans' },
  { path: '/en/items/Ale/', desc: 'ItemDetail(Ale)(en)', lang: 'en' },
  { path: '/ja/items/Ale/', desc: 'ItemDetail(Ale)(ja)', lang: 'ja' },
  {
    path: '/zh-Hans/lootdrops/HeaterShield_8001/',
    desc: 'LootdropDetail',
    lang: 'zh-Hans',
    expectedHrefs: ['/zh-Hans/lootdrops/HeaterShield_7001/'],
  },
  {
    path: '/zh-Hans/lootdrops/Spellbook_7001/',
    desc: 'LootdropDetail(Spellbook unique)',
    lang: 'zh-Hans',
    expectedHrefs: ['/zh-Hans/lootdrops/Spellbook_8001/'],
  },
  {
    path: '/zh-Hans/lootdrops/Spellbook_8001/',
    desc: 'LootdropDetail(Spellbook artifact)',
    lang: 'zh-Hans',
    expectedHrefs: ['/zh-Hans/lootdrops/Spellbook_7001/'],
  },
  {
    path: '/en/lootdrops/HeaterShield_8001/',
    desc: 'LootdropDetail(en)',
    lang: 'en',
  },
  {
    path: '/ja/lootdrops/HeaterShield_8001/',
    desc: 'LootdropDetail(ja)',
    lang: 'ja',
  },
  {
    path: '/ja/lootdrops/CastillonDagger_5001/',
    desc: 'LootdropDetail(CastillonDagger)(ja)',
    lang: 'ja',
    textChecks: [
      { pattern: /神秘の宝物庫の武器 \(1\)/, expected: true },
      { pattern: /黄金部屋の武器 \(1\)/, expected: true },
      {
        pattern:
          /技術オブジェクト: Weapon (?:Mystical Treasure Room|Golden Room)/,
        expected: false,
      },
    ],
  },
  {
    path: '/zh-Hant/lootdrops/CastillonDagger_5001/',
    desc: 'LootdropDetail(CastillonDagger)(zh-Hant)',
    lang: 'zh-Hant',
    textChecks: [
      { pattern: /神秘寶藏房-武器 \(1\)/, expected: true },
      { pattern: /黃金房-武器 \(1\)/, expected: true },
      {
        pattern: /技術物件：Weapon (?:Mystical Treasure Room|Golden Room)/,
        expected: false,
      },
    ],
  },
  {
    // Epic Bandage now has drops; use the absent legendary variant for this regression.
    path: '/en/lootdrops/Bandage_6001/',
    desc: 'LootdropDetail(Bandage)(en)',
    lang: 'en',
    textChecks: [
      { pattern: /Drop rate: 0%/, expected: true },
      { pattern: /\(\d+ positions\)/, expected: false },
      { pattern: /\(\d+点(?:选\d+)?\)/, expected: false },
    ],
    expectedHrefs: ['/en/lootdrops/Bandage_4001/'],
    forbiddenHrefs: ['/en/lootdrops/Bandage_6001/'],
  },
  {
    path: '/zh-Hans/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    desc: 'ModuleDetail',
    lang: 'zh-Hans',
    staticDescriptionChecks: [/包含 \d+ 个实体/, /和 \d+ 个位置点/],
  },
  {
    path: '/en/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    desc: 'ModuleDetail(en)',
    lang: 'en',
    staticDescriptionChecks: [/with \d+ entities/, /and \d+ positions/],
  },
  {
    path: '/ja/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    desc: 'ModuleDetail(ja)',
    lang: 'ja',
    staticDescriptionChecks: [/\d+ エンティティ/, /\d+ 地点/],
  },
];

const HYDRATION_RE =
  /hydration|did not match|#(?:418|423|425)|invariant=(?:418|423|425)/i;

function isIgnoredExternal(url) {
  return url.includes('cloudflareinsights.com');
}

function isGenericResourceError(message) {
  return /^Failed to load resource:/i.test(message);
}

async function contentLinkCount(page, href) {
  return page
    .locator(`a[href=${JSON.stringify(href)}]`)
    .evaluateAll(
      (links) =>
        links.filter((link) => !link.closest('.language-selector-details'))
          .length
    );
}

async function testPage(
  browser,
  {
    path,
    desc,
    lang,
    textChecks = [],
    staticDescriptionChecks = [],
    expectedHrefs = [],
    forbiddenHrefs = [],
  }
) {
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const resourceErrors = [];
  const ignoredExternalFailures = new Set();

  page.on('console', (msg) => {
    if (msg.type() === 'error' && !isIgnoredExternal(msg.text())) {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => pageErrors.push(err.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (isIgnoredExternal(url)) {
      ignoredExternalFailures.add(url);
    } else if (url.startsWith(BASE)) {
      resourceErrors.push(
        `${url}: ${request.failure()?.errorText ?? 'failed'}`
      );
    }
  });
  page.on('response', (response) => {
    const url = response.url();
    if (
      url.startsWith(BASE) &&
      url.includes('/data/') &&
      response.status() >= 400
    ) {
      resourceErrors.push(`${url}: HTTP ${response.status()}`);
    }
  });

  try {
    const staticResponse = await fetch(`${BASE}${path}`);
    if (!staticResponse.ok)
      throw new Error(`static HTTP ${staticResponse.status}`);
    const staticHtml = await staticResponse.text();
    const staticDescription = staticHtml.match(
      /<meta[^>]+name="description"[^>]+content="([^"]*)"/i
    )?.[1];
    const staticOgDescription = staticHtml.match(
      /<meta[^>]+property="og:description"[^>]+content="([^"]*)"/i
    )?.[1];
    if (!staticDescription || !staticOgDescription)
      throw new Error('missing static description metadata');
    if (staticDescription !== staticOgDescription)
      throw new Error('static description and OG description differ');
    for (const pattern of staticDescriptionChecks) {
      if (!pattern.test(staticDescription)) {
        throw new Error(`static description check failed: ${pattern}`);
      }
    }
    const response = await page.goto(`${BASE}${path}`, {
      waitUntil: 'domcontentloaded',
      timeout: TIMEOUT,
    });
    if (!response?.ok())
      throw new Error(`document HTTP ${response?.status() ?? 'none'}`);

    await page.locator('#root').waitFor({ state: 'visible', timeout: TIMEOUT });
    const placeholder = EXPECTED_PLACEHOLDER[lang];
    await page
      .locator(`input[placeholder=${JSON.stringify(placeholder)}]`)
      .first()
      .waitFor({ state: 'visible', timeout: TIMEOUT });
    await page.waitForFunction(
      () => !document.querySelector('#root [aria-busy="true"]'),
      undefined,
      { timeout: TIMEOUT }
    );

    const title = await page.title();
    const htmlLang = await page.locator('html').getAttribute('lang');
    const description = await page
      .locator('meta[name="description"]')
      .getAttribute('content');
    if (desc === 'HomePage(zh-Hans)') {
      const keywords = await page
        .locator('meta[name="keywords"]')
        .getAttribute('content');
      if (!keywords?.includes('dnd闪电指南')) {
        throw new Error(`missing homepage keyword: ${keywords}`);
      }
    }
    const ogDescription = await page
      .locator('meta[property="og:description"]')
      .getAttribute('content');
    const rootText = (await page.locator('#root').innerText()).trim();
    const hydrationErrors = [...pageErrors, ...consoleErrors].filter((error) =>
      HYDRATION_RE.test(error)
    );
    const filteredConsoleErrors = consoleErrors.filter(
      (error) =>
        !(isGenericResourceError(error) && ignoredExternalFailures.size > 0)
    );
    const errors = [...pageErrors, ...filteredConsoleErrors, ...resourceErrors];
    const hasTitle = title.length > 0 && title !== 'DarkFlashNav';

    if (htmlLang !== lang) throw new Error(`html lang=${htmlLang}`);
    if (!hasTitle) throw new Error(`invalid title=${JSON.stringify(title)}`);
    if (!rootText) throw new Error('empty root');
    for (const { pattern, expected } of textChecks) {
      if (pattern.test(rootText) !== expected) {
        throw new Error(`text check failed: ${pattern} expected=${expected}`);
      }
    }
    for (const href of expectedHrefs) {
      if ((await contentLinkCount(page, href)) === 0) {
        throw new Error(`missing link: ${href}`);
      }
    }
    for (const href of forbiddenHrefs) {
      if ((await contentLinkCount(page, href)) > 0) {
        throw new Error(`unexpected link: ${href}`);
      }
    }
    if (!description || !ogDescription)
      throw new Error('missing client description metadata');
    if (description !== ogDescription)
      throw new Error('client description and OG description differ');
    if (hydrationErrors.length)
      throw new Error(`hydration: ${hydrationErrors.join(' | ')}`);
    if (errors.length) throw new Error(errors.join(' | '));

    return { desc, lang, title, ok: true };
  } catch (error) {
    return { desc, lang, title: '', ok: false, error: error.message };
  } finally {
    await page.close();
  }
}

function denseModuleHoverTarget() {
  const dataDir = path.join(REPO_ROOT, 'data', 'json');
  const moduleName = 'ShipGraveyard_PiratePrison';
  const modules = JSON.parse(
    fs.readFileSync(path.join(dataDir, 'dungeon_modules.json'), 'utf8')
  );
  const module = modules.find((entry) => entry.name === moduleName);
  if (!module) throw new Error(`missing test module: ${moduleName}`);

  const coordsData = JSON.parse(
    fs.readFileSync(
      path.join(dataDir, 'dungeon_modules_coords', `${moduleName}.json`),
      'utf8'
    )
  );
  const locale = JSON.parse(
    fs.readFileSync(path.join(dataDir, 'locale', 'zh-Hans.json'), 'utf8')
  );
  const entities = coordsData.entities ?? [];
  const totalPoints = entities.reduce(
    (count, entity) => count + (entity.coords?.length ?? 0),
    0
  );
  const sx = module.size_x || 1;
  const sy = module.size_y || 1;
  const range = module.range || Math.max(sx, sy) * 1600 || 1600;
  const centerX = sx === 1 && sy === 2 ? 100 : 50;
  const multX = centerX;
  const titles = new Set();
  let target = null;

  for (const entity of entities) {
    const title =
      locale[entity.translation_key] || entity.translation || entity.name;
    if (title) titles.add(title);
    for (const coord of entity.coords ?? []) {
      let x = coord.x;
      let y = coord.y;
      const rotation = (((module.rotate || 0) % 360) * Math.PI) / 180;
      if (rotation !== 0) {
        const cos = Math.cos(rotation);
        const sin = Math.sin(rotation);
        const nextX = x * cos - y * sin;
        const nextY = x * sin + y * cos;
        x = nextX;
        y = nextY;
      }
      x += module.offset_x || 0;
      y += module.offset_y || 0;
      const px = centerX + (x / range) * multX;
      const py = 50 + (y / range) * 50;
      if (!target && px > 2 && px < 98 && py > 2 && py < 98 && title) {
        target = { px, py };
      }
    }
  }

  if (!target) throw new Error(`no visible dot in test module: ${moduleName}`);
  return { totalPoints, target, titles: [...titles] };
}

async function testDenseMapLayer(browser) {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
  });
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  try {
    const data = denseModuleHoverTarget();
    if (data.totalPoints <= 300) {
      throw new Error(
        `test module no longer exceeds canvas threshold: ${data.totalPoints}`
      );
    }
    const response = await page.goto(
      `${BASE}/zh-Hans/dungeon_modules/ShipGraveyard/ShipGraveyard_PiratePrison/`,
      { waitUntil: 'domcontentloaded', timeout: TIMEOUT }
    );
    if (!response?.ok()) {
      throw new Error(`document HTTP ${response?.status() ?? 'none'}`);
    }

    await page.getByRole('button', { name: '显示全部' }).click();
    const canvas = page.locator('canvas[data-map-dot-canvas]');
    await page.waitForFunction(
      (count) => {
        const rendered = document.querySelector('canvas[data-map-dot-canvas]');
        return (
          rendered?.dataset.rendered === 'true' &&
          Number(rendered.dataset.dotCount) === count
        );
      },
      data.totalPoints,
      { timeout: TIMEOUT }
    );
    const domDotCount = await page
      .locator(
        '#root div[style*="width: 9px"][style*="height: 9px"][style*="border-radius: 50%"]'
      )
      .count();
    if (domDotCount !== 0) {
      throw new Error(`dense map still has ${domDotCount} per-dot DOM nodes`);
    }

    const box = await canvas.boundingBox();
    if (!box) throw new Error('dense map canvas has no visible bounds');
    await page.mouse.move(
      box.x + (data.target.px / 100) * box.width,
      box.y + (data.target.py / 100) * box.height
    );
    const tooltip = page.locator('#root [role="tooltip"]');
    await tooltip.waitFor({ state: 'visible', timeout: TIMEOUT });
    const tooltipText = (await tooltip.textContent())?.trim() ?? '';
    if (!data.titles.includes(tooltipText)) {
      throw new Error(
        `unexpected canvas tooltip: ${JSON.stringify(tooltipText)}`
      );
    }

    await page.setViewportSize({ width: 1100, height: 900 });
    await page.waitForFunction(
      () => {
        const rendered = document.querySelector('canvas[data-map-dot-canvas]');
        if (!rendered) return false;
        const bounds = rendered.getBoundingClientRect();
        const scale = window.devicePixelRatio || 1;
        return (
          rendered.width === Math.round(bounds.width * scale) &&
          rendered.height === Math.round(bounds.height * scale)
        );
      },
      undefined,
      { timeout: TIMEOUT }
    );
    if (pageErrors.length) throw new Error(pageErrors.join(' | '));
    return { ok: true, dots: data.totalPoints, tooltip: tooltipText };
  } catch (error) {
    return { ok: false, error: error.message };
  } finally {
    await page.close();
  }
}

async function testLargeLootdropReferenceLoading(browser) {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const pageErrors = [];
  const refStatuses = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('response', (response) => {
    const url = response.url();
    if (
      url.includes('/data/') &&
      /\/(props|monsters|items)\/[^/]+\.json(?:\?|$)/.test(url)
    ) {
      refStatuses.push(response.status());
    }
  });

  try {
    const response = await page.goto(`${BASE}/en/lootdrops/GemNecklace_5001/`, {
      waitUntil: 'domcontentloaded',
      timeout: TIMEOUT,
    });
    if (!response?.ok()) {
      throw new Error(`document HTTP ${response?.status() ?? 'none'}`);
    }
    await page.waitForFunction(
      () => {
        const busy = [...document.querySelectorAll('#root [aria-busy]')];
        return (
          busy.length > 0 &&
          busy.every((element) => element.getAttribute('aria-busy') === 'false')
        );
      },
      undefined,
      { timeout: TIMEOUT }
    );
    if (refStatuses.some((status) => status >= 400)) {
      throw new Error(
        `coordinate ref HTTP failures: ${refStatuses.join(', ')}`
      );
    }

    const toggle = page.getByRole('button', {
      name: /^(Show All|Hide All)$/,
    });
    await toggle.waitFor({ state: 'visible', timeout: TIMEOUT });
    const initialLabel = (await toggle.textContent())?.trim();
    if (initialLabel !== 'Show All' && initialLabel !== 'Hide All') {
      throw new Error(`unexpected source toggle label: ${initialLabel}`);
    }
    const nextLabel = initialLabel === 'Show All' ? 'Hide All' : 'Show All';
    await toggle.click();
    await page
      .getByRole('button', { name: nextLabel, exact: true })
      .waitFor({ state: 'visible', timeout: TIMEOUT });

    if (pageErrors.length) throw new Error(pageErrors.join(' | '));
    return { ok: true, refs: refStatuses.length, initialLabel, nextLabel };
  } catch (error) {
    return { ok: false, error: error.message };
  } finally {
    await page.close();
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const failures = [];

  for (const pageConfig of PAGES) {
    const result = await testPage(browser, pageConfig);
    if (result.ok) {
      console.log(
        `PASS [${result.lang}] ${result.desc}: title=${JSON.stringify(result.title)}`
      );
    } else {
      failures.push(result);
      console.error(`FAIL [${result.lang}] ${result.desc}: ${result.error}`);
    }
  }

  const mapResult = await testDenseMapLayer(browser);
  if (mapResult.ok) {
    console.log(
      `PASS [zh-Hans] DenseMapCanvas: ${mapResult.dots} dots; tooltip=${JSON.stringify(mapResult.tooltip)}`
    );
  } else {
    failures.push({ desc: 'DenseMapCanvas', lang: 'zh-Hans', ...mapResult });
    console.error(`FAIL [zh-Hans] DenseMapCanvas: ${mapResult.error}`);
  }

  const lootdropResult = await testLargeLootdropReferenceLoading(browser);
  if (lootdropResult.ok) {
    console.log(
      `PASS [en] LootdropReferenceLoading: ${lootdropResult.refs} refs; ${lootdropResult.initialLabel} → ${lootdropResult.nextLabel}`
    );
  } else {
    failures.push({
      desc: 'LootdropReferenceLoading',
      lang: 'en',
      ...lootdropResult,
    });
    console.error(
      `FAIL [en] LootdropReferenceLoading: ${lootdropResult.error}`
    );
  }

  await browser.close();
  const testCount = PAGES.length + 2;
  console.log(
    `\nPass: ${testCount - failures.length}; Fail: ${failures.length}`
  );
  process.exit(failures.length ? 1 : 0);
}

main().catch((error) => {
  console.error('FATAL:', error);
  process.exit(1);
});
