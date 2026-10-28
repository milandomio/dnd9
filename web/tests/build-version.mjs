import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  collectBuildInputs,
  createBuildVersion,
} from '../scripts/buildVersion.mjs';

const root = mkdtempSync(join(tmpdir(), 'df5-release-'));
try {
  for (const dir of [
    'web/src',
    'web/scripts',
    'web/public',
    'data/json',
    'data/img',
  ])
    mkdirSync(join(root, dir), { recursive: true });
  writeFileSync(join(root, 'web/src/app.tsx'), 'export const value = 1;');
  writeFileSync(join(root, 'web/scripts/ssg.mjs'), 'build');
  writeFileSync(join(root, 'web/public/icon.png'), Buffer.from([1, 2, 3]));
  writeFileSync(join(root, 'web/public/data'), 'generated symlink placeholder');
  writeFileSync(
    join(root, 'data/json/items.json'),
    JSON.stringify({ items: [] })
  );
  writeFileSync(
    join(root, 'data/json/meta.json'),
    JSON.stringify({ generated: true })
  );
  writeFileSync(
    join(root, 'data/img/map.webp'),
    Buffer.from([0x52, 0x49, 0x46, 0x46])
  );
  writeFileSync(join(root, 'web/package-lock.json'), 'lock');

  const options = { base: '/', dataDate: '1700000000' };
  const inputs = collectBuildInputs(root, true, options);
  const paths = inputs.map(({ path }) => path);
  assert(paths.includes('web/src/app.tsx'));
  assert(paths.includes('data/json/items.json'));
  assert(paths.includes('data/img/map.webp'));
  assert(!paths.includes('data/json/meta.json'));
  assert(!paths.some((path) => path.startsWith('web/public/data/')));

  const version = createBuildVersion(inputs);
  assert.match(version, /^v[0-9a-f]{24}$/);
  assert.equal(createBuildVersion([...inputs].reverse()), version);
  for (const [path, replacement] of [
    ['web/src/app.tsx', 'export const value = 2;'],
    ['data/json/items.json', JSON.stringify({ items: [1] })],
    ['data/img/map.webp', Buffer.from([0x52, 0x49, 0x46, 0x46, 1])],
  ]) {
    writeFileSync(join(root, path), replacement);
    assert.notEqual(
      createBuildVersion(collectBuildInputs(root, true, options)),
      version,
      `${path} must invalidate the release`
    );
    writeFileSync(
      join(root, path),
      inputs.find((input) => input.path === path).content
    );
  }
  assert.notEqual(
    createBuildVersion(
      collectBuildInputs(root, true, { ...options, base: '/preview/' })
    ),
    version
  );
  assert.notEqual(
    createBuildVersion(
      collectBuildInputs(root, true, { ...options, dataDate: '1700000001' })
    ),
    version
  );
  assert.notEqual(
    createBuildVersion(
      collectBuildInputs(root, true, { ...options, seasonVersion: 11 })
    ),
    version,
    'season version must invalidate the release'
  );
} finally {
  rmSync(root, { recursive: true, force: true });
}

console.log('PASS build version covers code, JSON, and images');
