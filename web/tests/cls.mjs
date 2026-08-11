import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://localhost:8080';
const TIMEOUT = Number(process.env.CLS_TIMEOUT || 20000);
const BUDGET = Number(process.env.CLS_BUDGET || 0.1);
const FAIL_ON_CLS = process.env.FAIL_ON_CLS === '1';

const CASES = [
  { path: '/zh-Hans/', label: 'home-zh-Hans' },
  { path: '/en/', label: 'home-en' },
  { path: '/zh-Hans/items/', label: 'list-zh-Hans' },
  { path: '/en/items/', label: 'list-en' },
  { path: '/zh-Hans/items/Ale/', label: 'detail-zh-Hans' },
  { path: '/en/items/Ale/', label: 'detail-en' },
  {
    path: '/zh-Hans/lootdrops/HeaterShield_8001/',
    label: 'lootdrop-zh-Hans',
  },
  {
    path: '/en/lootdrops/HeaterShield_8001/',
    label: 'lootdrop-en',
  },
  {
    path: '/zh-Hans/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/',
    label: 'module-detail-zh-Hans',
  },
];

const VIEWPORTS = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 900 },
];

function installObserver() {
  window.__darkFindCls = { entries: [] };
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) {
        window.__darkFindCls.entries.push({
          value: entry.value,
          startTime: entry.startTime,
          sources: entry.sources.map((source) => ({
            node: source.node
              ? {
                  tag: source.node.tagName,
                  id: source.node.id,
                  className:
                    typeof source.node.className === 'string'
                      ? source.node.className
                      : '',
                  text: (source.node.textContent || '').trim().slice(0, 80),
                }
              : null,
            previousRect: source.previousRect
              ? {
                  x: source.previousRect.x,
                  y: source.previousRect.y,
                  width: source.previousRect.width,
                  height: source.previousRect.height,
                }
              : null,
            currentRect: source.currentRect
              ? {
                  x: source.currentRect.x,
                  y: source.currentRect.y,
                  width: source.currentRect.width,
                  height: source.currentRect.height,
                }
              : null,
          })),
        });
      }
    }
  });
  observer.observe({ type: 'layout-shift', buffered: true });
}

async function measure(page) {
  return page.evaluate(() => {
    const entries = window.__darkFindCls?.entries ?? [];
    const windows = entries
      .sort((a, b) => a.startTime - b.startTime)
      .reduce((result, entry) => {
        const previous = result.at(-1);
        if (
          !previous ||
          entry.startTime - previous.lastTime > 1000 ||
          entry.startTime - previous.startTime > 5000
        ) {
          result.push({
            startTime: entry.startTime,
            lastTime: entry.startTime,
            value: entry.value,
            entries: [entry],
          });
        } else {
          previous.lastTime = entry.startTime;
          previous.value += entry.value;
          previous.entries.push(entry);
        }
        return result;
      }, []);
    const body = getComputedStyle(document.body);
    return {
      entries,
      windows,
      bodyMargin: body.margin,
      rootRect: document
        .querySelector('#root')
        ?.getBoundingClientRect()
        .toJSON(),
    };
  });
}

async function waitForStablePage(page) {
  await page.locator('#root').waitFor({ state: 'visible', timeout: TIMEOUT });
  await page
    .waitForFunction(
      () => !document.querySelector('#root [aria-busy="true"]'),
      undefined,
      { timeout: TIMEOUT }
    )
    .catch(() => {});
  await page.waitForTimeout(1500);
}

async function runCase(browser, testCase, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
  });
  const page = await context.newPage();
  await page.addInitScript(installObserver);
  const url = `${BASE}${testCase.path}`;
  try {
    const response = await page.goto(url, {
      waitUntil: 'domcontentloaded',
      timeout: TIMEOUT,
    });
    if (!response?.ok()) {
      throw new Error(`HTTP ${response?.status() ?? 'none'}`);
    }
    await waitForStablePage(page);
    const result = await measure(page);
    const cls = result.entries.reduce((sum, entry) => sum + entry.value, 0);
    const topWindow = Math.max(
      0,
      ...result.windows.map((window) => window.value)
    );
    const output = {
      label: testCase.label,
      viewport: viewport.name,
      url,
      cls: Number(cls.toFixed(5)),
      largestSessionWindow: Number(topWindow.toFixed(5)),
      shiftCount: result.entries.length,
      bodyMargin: result.bodyMargin,
      rootRect: result.rootRect,
      windows: result.windows,
    };
    const status = cls > BUDGET ? 'WARN' : 'PASS';
    console.log(`${status} ${JSON.stringify(output)}`);
    return { ...output, failed: cls > BUDGET };
  } finally {
    await context.close();
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const testCase of CASES) {
      for (const viewport of VIEWPORTS) {
        results.push(await runCase(browser, testCase, viewport));
      }
    }
  } finally {
    await browser.close();
  }
  const failed = results.filter((result) => result.failed);
  console.log(
    `CLS baseline complete: ${results.length} cases, ${failed.length} over budget ${BUDGET}`
  );
  if (FAIL_ON_CLS && failed.length > 0) process.exitCode = 1;
}

main().catch((error) => {
  console.error(`FAIL CLS baseline: ${error.stack || error.message}`);
  process.exitCode = 1;
});
