import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://localhost:8080';
const TIMEOUT = 20000;
const EXPECTED_PLACEHOLDER = {
  'zh-Hans': '搜索物品/怪物/实体...',
  en: 'Search items/monsters/props...',
  ja: 'アイテム/モンスターを検索...',
};

const PAGES = [
  { path: '/zh-Hans/', desc: 'HomePage', lang: 'zh-Hans' },
  { path: '/en/', desc: 'HomePage(en)', lang: 'en' },
  { path: '/ja/', desc: 'HomePage(ja)', lang: 'ja' },
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
    path: '/en/lootdrops/Bandage_5001/',
    desc: 'LootdropDetail(Bandage)(en)',
    lang: 'en',
    textChecks: [
      { pattern: /\(\d+ positions\)/, expected: true },
      { pattern: /\(\d+ positions choose \d+\)/, expected: true },
      { pattern: /Composite Rate \d/, expected: true },
      { pattern: /\(\d+点(?:选\d+)?\)/, expected: false },
    ],
  },
  {
    path: '/zh-Hans/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    desc: 'ModuleDetail',
    lang: 'zh-Hans',
  },
  {
    path: '/en/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    desc: 'ModuleDetail(en)',
    lang: 'en',
  },
  {
    path: '/ja/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    desc: 'ModuleDetail(ja)',
    lang: 'ja',
  },
];

const HYDRATION_RE =
  /hydration|did not match|#(?:418|423|425)|invariant=(?:418|423|425)/i;

function isIgnoredExternal(url) {
  return url.includes('cloudflareinsights.com');
}

async function testPage(browser, { path, desc, lang, textChecks = [] }) {
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const resourceErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error' && !isIgnoredExternal(msg.text())) {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => pageErrors.push(err.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (url.startsWith(BASE) && !isIgnoredExternal(url)) {
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
      () => !document.querySelector('#root > [aria-busy="true"]'),
      undefined,
      { timeout: TIMEOUT }
    );

    const title = await page.title();
    const htmlLang = await page.locator('html').getAttribute('lang');
    const rootText = (await page.locator('#root').innerText()).trim();
    const hydrationErrors = [...pageErrors, ...consoleErrors].filter((error) =>
      HYDRATION_RE.test(error)
    );
    const errors = [...pageErrors, ...consoleErrors, ...resourceErrors];
    const hasTitle = title.length > 0 && title !== 'DarkFlashNav';

    if (htmlLang !== lang) throw new Error(`html lang=${htmlLang}`);
    if (!hasTitle) throw new Error(`invalid title=${JSON.stringify(title)}`);
    if (!rootText) throw new Error('empty root');
    for (const { pattern, expected } of textChecks) {
      if (pattern.test(rootText) !== expected) {
        throw new Error(`text check failed: ${pattern} expected=${expected}`);
      }
    }
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

  await browser.close();
  console.log(
    `\nPass: ${PAGES.length - failures.length}; Fail: ${failures.length}`
  );
  process.exit(failures.length ? 1 : 0);
}

main().catch((error) => {
  console.error('FATAL:', error);
  process.exit(1);
});
