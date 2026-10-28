import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join, sep } from 'node:path';

const BUILD_FILES = [
  'web/index.html',
  'web/package.json',
  'web/package-lock.json',
  'web/vite.config.ts',
  'web/scripts/ssg.mjs',
  'web/scripts/buildVersion.mjs',
];

export function collectBuildInputs(root, quick = false, options = {}) {
  const inputs = [];
  const seen = new Set();

  function addFile(path) {
    if (seen.has(path)) return;
    seen.add(path);
    inputs.push({ path, content: readFileSync(join(root, path)) });
  }

  function addTree(path, { skipMeta = false, skipPublicData = false } = {}) {
    let entries;
    try {
      entries = readdirSync(join(root, path), { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const child = `${path}/${entry.name}`;
      if (skipPublicData && entry.name === 'data') continue;
      if (entry.isDirectory()) addTree(child, { skipMeta });
      else if (entry.isFile() && !(skipMeta && entry.name === 'meta.json'))
        addFile(child.split(sep).join('/'));
    }
  }

  for (const path of BUILD_FILES) {
    try {
      addFile(path);
    } catch {
      // Optional build inputs may not exist in isolated test fixtures.
    }
  }
  addTree('web/src');
  addTree('web/public', { skipPublicData: true });
  addTree('data/json', { skipMeta: true });
  addTree('data/img');
  inputs.push({
    path: 'build-options',
    content: JSON.stringify({ mode: quick ? 'quick' : 'full', ...options }),
  });
  return inputs;
}

export function createBuildVersion(inputs) {
  const hash = createHash('sha256');
  const ordered = [...inputs].sort((a, b) =>
    a.path < b.path ? -1 : a.path > b.path ? 1 : 0
  );

  for (const input of ordered) {
    const path = Buffer.from(input.path);
    const content = Buffer.from(input.content);
    hash.update(String(path.length));
    hash.update(':');
    hash.update(path);
    hash.update(String(content.length));
    hash.update(':');
    hash.update(content);
  }

  return `v${hash.digest('hex').slice(0, 24)}`;
}
