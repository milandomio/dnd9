import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(
  new URL('../src/utils/dataUrl.ts', import.meta.url),
  'utf8'
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2020,
  },
});
const moduleUrl =
  'data:text/javascript;base64,' + Buffer.from(outputText).toString('base64');
const { dataUrl } = await import(moduleUrl);

assert.equal(
  dataUrl('v0123456789abcdef01234567', '/data/json/items.json'),
  '/data/r-v0123456789abcdef01234567/json/items.json'
);
assert.equal(
  dataUrl('v0123456789abcdef01234567', '/data/img/Map.webp'),
  '/data/r-v0123456789abcdef01234567/img/Map.webp'
);
assert.equal(
  dataUrl('dev', '/data/json/index.json'),
  '/data/dev/json/index.json'
);
assert.equal(
  dataUrl('1700000000', '/data/json/items.json'),
  '/data/s44we8/json/items.json'
);

console.log('PASS data URL version mapping');
