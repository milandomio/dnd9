import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { chromium } from 'playwright';

const DIST = resolve(new URL('../dist', import.meta.url).pathname);
const manifest = JSON.parse(
  await readFile(resolve(DIST, 'data/json/meta.json'), 'utf8')
);
const deployedVersion = manifest.version;
const legacyDataVersion = Number(manifest.dataDate).toString(36);
const redirectRules = (
  await readFile(resolve(DIST, '_redirects'), 'utf8')
).split('\n');
const headerText = await readFile(resolve(DIST, '_headers'), 'utf8');
const headerRules = headerText
  .trim()
  .split(/\n\s*\n/)
  .map((block) => {
    const [pattern, ...headers] = block.split('\n');
    return { pattern, headers };
  });
assert.match(deployedVersion, /^v[0-9a-f]{24}$/);
assert(
  headerRules.every(({ pattern }) => (pattern.match(/\*/g) ?? []).length <= 1)
);
assert(!headerRules.some(({ pattern }) => pattern === '/*'));
assert(headerRules.some(({ pattern }) => pattern === '/data/r-*'));
assert(
  redirectRules.includes(
    '/data/' +
      legacyDataVersion +
      '/json/* /data/r-' +
      deployedVersion +
      '/json/:splat 302'
  )
);
assert(
  redirectRules.includes(
    '/data/img/* /data/r-' + deployedVersion + '/img/:splat 302'
  )
);
assert(
  headerRules.some(
    ({ pattern }) => pattern === '/data/' + legacyDataVersion + '/json/*'
  )
);
const oldVersion =
  deployedVersion === 'v000000000000000000000000'
    ? 'v111111111111111111111111'
    : 'v000000000000000000000000';
const requests = new Map();
let activeVersion = oldVersion;
let releaseManifest = new Promise((resolve) => {
  globalThis.releaseManifest = resolve;
});
let holdManifest = true;
const types = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webmanifest': 'application/manifest+json',
  '.webp': 'image/webp',
};

function cacheControlFor(pathname) {
  const matching = headerRules.filter(({ pattern }) => {
    const star = pattern.indexOf('*');
    if (star < 0) return pattern === pathname;
    const prefix = pattern.slice(0, star);
    const suffix = pattern.slice(star + 1);
    return (
      pathname.startsWith(prefix) &&
      pathname.endsWith(suffix) &&
      pathname.length >= prefix.length + suffix.length
    );
  });
  assert(
    matching.length <= 1,
    'overlapping Pages header rules for ' + pathname
  );
  const value = matching[0]?.headers
    .map((header) => header.trim())
    .find((header) => header.startsWith('Cache-Control:'));
  return value
    ? value.slice('Cache-Control:'.length).trim()
    : 'public, max-age=0';
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  requests.set(url.pathname, (requests.get(url.pathname) ?? 0) + 1);
  try {
    if (url.pathname === '/data/json/meta.json') {
      if (holdManifest) {
        await releaseManifest;
        holdManifest = false;
      }
      response.writeHead(200, {
        'Content-Type': types['.json'],
        'Cache-Control': 'no-store',
      });
      response.end(JSON.stringify({ ...manifest, version: activeVersion }));
      return;
    }

    let pathname = decodeURIComponent(url.pathname);
    const legacyJsonPrefix = '/data/' + legacyDataVersion + '/json/';
    if (
      pathname.startsWith(legacyJsonPrefix) ||
      pathname.startsWith('/data/img/')
    ) {
      const destination = pathname.startsWith(legacyJsonPrefix)
        ? '/data/r-' +
          deployedVersion +
          '/json/' +
          pathname.slice(legacyJsonPrefix.length)
        : '/data/r-' +
          deployedVersion +
          '/img/' +
          pathname.slice('/data/img/'.length);
      response
        .writeHead(302, {
          Location: destination,
          'Cache-Control': cacheControlFor(pathname),
        })
        .end();
      return;
    }
    const oldAsset = pathname.startsWith('/old/assets/');
    if (oldAsset) pathname = pathname.slice('/old'.length);
    if (pathname.startsWith('/data/r-' + oldVersion + '/'))
      pathname = pathname.replace(
        '/data/r-' + oldVersion + '/',
        '/data/r-' + deployedVersion + '/'
      );
    if (pathname === '/') pathname = '/index.html';
    else if (pathname.endsWith('/')) pathname += 'index.html';

    const filePath = resolve(DIST, '.' + pathname);
    if (!filePath.startsWith(DIST + sep)) {
      response.writeHead(400).end();
      return;
    }
    const fileStat = await stat(filePath);
    if (!fileStat.isFile()) {
      response.writeHead(404).end();
      return;
    }
    let body = await readFile(filePath);
    const ext = extname(filePath);
    if (activeVersion === oldVersion && ext === '.html')
      body = Buffer.from(
        body
          .toString('utf8')
          .replaceAll(deployedVersion, oldVersion)
          .replaceAll('/assets/', '/old/assets/')
      );
    else if (activeVersion === oldVersion && oldAsset && ext === '.js')
      body = Buffer.from(
        body.toString('utf8').replaceAll(deployedVersion, oldVersion)
      );
    else if (activeVersion === oldVersion && pathname === '/sw.js')
      body = Buffer.from(
        body.toString('utf8').replaceAll(deployedVersion, oldVersion)
      );
    response.writeHead(200, {
      'Content-Type': types[ext] ?? 'application/octet-stream',
      'Cache-Control': cacheControlFor(pathname),
    });
    response.end(body);
  } catch (error) {
    if (response.headersSent) return response.destroy(error);
    response.writeHead(404).end();
  }
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const address = server.address();
const base = 'http://127.0.0.1:' + address.port;
for (const [legacyPath, expectedPath] of [
  [
    '/data/' + legacyDataVersion + '/json/dungeon_modules.json',
    '/data/r-' + deployedVersion + '/json/dungeon_modules.json',
  ],
  [
    '/data/img/RareModule_1x1.webp',
    '/data/r-' + deployedVersion + '/img/RareModule_1x1.webp',
  ],
]) {
  const redirect = await fetch(base + legacyPath, { redirect: 'manual' });
  assert.equal(redirect.status, 302, legacyPath + ' should redirect');
  assert.equal(redirect.headers.get('cache-control'), 'no-store');
  assert.equal(redirect.headers.get('location'), expectedPath);
  const final = await fetch(base + legacyPath);
  assert.equal(final.status, 200, expectedPath + ' should resolve');
  assert.equal(new URL(final.url).pathname, expectedPath);
}
requests.clear();
const browser = await chromium.launch({ headless: true });

try {
  const context = await browser.newContext({ serviceWorkers: 'allow' });
  await context.route('https://**/*', (route) => route.abort());
  const page = await context.newPage();
  let pageNavigations = 0;
  page.on('framenavigated', (frame) => {
    if (frame === page.mainFrame()) pageNavigations += 1;
  });

  const startedAt = Date.now();
  await page.goto(base + '/zh-Hans/', {
    waitUntil: 'domcontentloaded',
    timeout: 15000,
  });
  assert(
    Date.now() - startedAt < 4000,
    'a pending release check must not block the document'
  );
  assert(
    await page.locator('#root').innerText(),
    'SSG page should render before the release check'
  );
  assert.equal(
    await page.locator('meta[name="df5-version"]').getAttribute('content'),
    oldVersion
  );
  await page.waitForFunction(
    async () =>
      (await navigator.serviceWorker?.getRegistration())?.active?.state ===
      'activated',
    null,
    { timeout: 20000 }
  );
  if (
    !(await page.evaluate(() => Boolean(navigator.serviceWorker?.controller)))
  )
    await page.reload({ waitUntil: 'domcontentloaded' });
  try {
    await page.waitForFunction(
      () => Boolean(navigator.serviceWorker?.controller),
      null,
      { timeout: 15000 }
    );
  } catch (error) {
    const diagnostic = await page.evaluate(async () => {
      const registrations = await navigator.serviceWorker.getRegistrations();
      return {
        url: location.href,
        controller: navigator.serviceWorker.controller?.scriptURL ?? null,
        registrations: registrations.map((registration) => ({
          scope: registration.scope,
          active: registration.active?.state ?? null,
          waiting: registration.waiting?.state ?? null,
          installing: registration.installing?.state ?? null,
        })),
      };
    });
    console.error('SW_DIAGNOSTIC', JSON.stringify(diagnostic));
    console.error('ORIGIN_REQUESTS', JSON.stringify([...requests.entries()]));
    throw error;
  }
  assert.equal(
    requests.get('/data/NaN/json/dungeon_modules.json') ?? 0,
    0,
    'all JSON loaders must use the release URL mapper'
  );
  assert(
    (requests.get('/data/r-' + oldVersion + '/json/dungeon_modules.json') ??
      0) > 0,
    'module data should request the active release path'
  );
  pageNavigations = 0;
  requests.clear();

  activeVersion = deployedVersion;
  globalThis.releaseManifest();
  await page.waitForFunction(
    (version) =>
      document
        .querySelector('meta[name="df5-version"]')
        ?.getAttribute('content') === version,
    deployedVersion,
    { timeout: 30000 }
  );
  assert.equal(
    pageNavigations,
    1,
    'the prepared release should trigger exactly one reload'
  );
  assert.equal(
    requests.get('/zh-Hans/') ?? 0,
    1,
    'the update probe should be the only origin HTML request'
  );
  assert.equal(
    await page.evaluate(() => sessionStorage.getItem('df5_applied_version')),
    deployedVersion
  );

  const jsonUrl = '/data/r-' + deployedVersion + '/json/dungeon_modules.json';
  const imageUrl = '/data/r-' + deployedVersion + '/img/RareModule_1x1.webp';
  for (const resource of [jsonUrl, imageUrl]) {
    const result = await page.evaluate(async (url) => {
      const response = await fetch(url);
      return { ok: response.ok, status: response.status };
    }, resource);
    assert.equal(
      result.ok,
      true,
      resource + ' must be available and cacheable'
    );
  }
  requests.clear();
  const steadyStartedAt = Date.now();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('#root').waitFor({ state: 'visible' });
  assert(
    Date.now() - steadyStartedAt < 1500,
    'cached navigation should not wait on the origin'
  );
  assert.equal(
    requests.get('/zh-Hans/') ?? 0,
    0,
    'same-version HTML should be local-first'
  );
  assert.equal(
    requests.get(jsonUrl) ?? 0,
    0,
    'same-version JSON should be local-first'
  );
  assert.equal(
    requests.get(imageUrl) ?? 0,
    0,
    'same-version images should be local-first'
  );
  console.log(
    'PASS delayed version check, one-step release switch, and local-first cache'
  );
  await context.close();
} finally {
  globalThis.releaseManifest();
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
