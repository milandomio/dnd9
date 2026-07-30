import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://localhost:8080';
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
      { pattern: /Drop rate: 0%/, expected: true },
      { pattern: /\(\d+ positions\)/, expected: false },
      { pattern: /\(\d+点(?:选\d+)?\)/, expected: false },
    ],
    expectedHrefs: ['/en/lootdrops/Bandage_4001/'],
    forbiddenHrefs: ['/en/lootdrops/Bandage_5001/'],
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

function isGenericResourceError(message) {
  return /^Failed to load resource:/i.test(message);
}

async function testPage(
  browser,
  { path, desc, lang, textChecks = [], expectedHrefs = [], forbiddenHrefs = [] }
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
    const description = await page
      .locator('meta[name="description"]')
      .getAttribute('content');
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
      if (
        (await page.locator(`a[href=${JSON.stringify(href)}]`).count()) === 0
      ) {
        throw new Error(`missing link: ${href}`);
      }
    }
    for (const href of forbiddenHrefs) {
      if ((await page.locator(`a[href=${JSON.stringify(href)}]`).count()) > 0) {
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
