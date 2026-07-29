import { existsSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const key = process.env.INDEXNOW_KEY?.trim();

if (!key) {
  console.log('[indexnow] INDEXNOW_KEY is not set; skipping key file');
  process.exit(0);
}

if (!/^[A-Za-z0-9-]{8,128}$/.test(key)) {
  throw new Error(
    '[indexnow] INDEXNOW_KEY must contain 8-128 letters, numbers, or dashes'
  );
}

const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
if (!existsSync(dist)) {
  throw new Error('[indexnow] web/dist does not exist; run the build first');
}

writeFileSync(join(dist, `${key}.txt`), `${key}\n`, 'utf8');
console.log(`[indexnow] wrote ${key}.txt to dist/`);
