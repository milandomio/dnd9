import { existsSync, readFileSync, readdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const SITE = (process.env.INDEXNOW_SITE || 'https://dnd9.icetar.com').replace(
  /\/$/,
  ''
);
const API =
  process.env.INDEXNOW_ENDPOINT || 'https://api.indexnow.org/indexnow';
const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const BATCH_SIZE = 10_000;
const MAX_ATTEMPTS = 3;
const RETRY_DELAY_MS = 5_000;
const KEY_FILE_RE = /^([A-Za-z0-9-]{8,128})\.txt$/;

function validateKey(key) {
  if (!/^[A-Za-z0-9-]{8,128}$/.test(key)) {
    throw new Error(
      '[indexnow] key must contain 8-128 letters, numbers, or dashes'
    );
  }
  return key;
}

function discoverKey() {
  if (!existsSync(dist)) return null;
  const keyFiles = readdirSync(dist).filter((file) => KEY_FILE_RE.test(file));
  if (keyFiles.length === 0) return null;
  if (keyFiles.length > 1) {
    throw new Error(
      `[indexnow] expected one key file in dist, found ${keyFiles.length}`
    );
  }

  const [, key] = keyFiles[0].match(KEY_FILE_RE);
  const content = readFileSync(join(dist, keyFiles[0]), 'utf8').trim();
  if (content !== key) {
    throw new Error(
      `[indexnow] key file ${keyFiles[0]} content does not match`
    );
  }
  return validateKey(key);
}

const key = discoverKey();
if (!key) {
  console.log('[indexnow] no key file found; skipping URL submission');
  process.exit(0);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const sitemapFiles = readdirSync(dist)
  .filter((file) => /^sitemap-.+\.xml$/.test(file))
  .sort();
const urls = new Set();

for (const file of sitemapFiles) {
  const xml = readFileSync(join(dist, file), 'utf8');
  for (const match of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) {
    urls.add(match[1].replaceAll('&amp;', '&'));
  }
}

const urlList = [...urls].filter((url) => {
  try {
    return new URL(url).origin === SITE;
  } catch {
    return false;
  }
});

if (sitemapFiles.length === 0 || urlList.length === 0) {
  throw new Error('[indexnow] no URLs found in generated language sitemaps');
}

async function submitBatch(batch, batchNumber, totalBatches) {
  const payload = {
    host: new URL(SITE).host,
    key,
    keyLocation: `${SITE}/${key}.txt`,
    urlList: batch,
  };

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const response = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      console.log(
        `[indexnow] batch ${batchNumber}/${totalBatches} accepted (${response.status}, ${batch.length} URLs)`
      );
      return;
    }

    const body = await response.text();
    if (attempt === MAX_ATTEMPTS) {
      throw new Error(
        `[indexnow] batch ${batchNumber} failed with ${response.status}: ${body}`
      );
    }
    console.warn(
      `[indexnow] batch ${batchNumber} returned ${response.status}; retrying (${attempt}/${MAX_ATTEMPTS - 1})`
    );
    await sleep(RETRY_DELAY_MS * attempt);
  }
}

const batches = [];
for (let i = 0; i < urlList.length; i += BATCH_SIZE) {
  batches.push(urlList.slice(i, i + BATCH_SIZE));
}

for (let i = 0; i < batches.length; i++) {
  await submitBatch(batches[i], i + 1, batches.length);
}

console.log(
  `[indexnow] submitted ${urlList.length} URLs from ${sitemapFiles.length} language sitemaps`
);
