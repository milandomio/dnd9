import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://localhost:8080';
const SEASON = 11;

async function main() {
  const manifest = await (await fetch(`${BASE}/data/json/meta.json`)).json();
  assert.equal(
    manifest.seasonVersion,
    SEASON,
    'meta.json must publish season 11'
  );
  assert.match(manifest.version, /^v[0-9a-f]{24}$/);
  const npcs = await (
    await fetch(`${BASE}/data/r-${manifest.version}/json/quest_npc.json`)
  ).json();
  const npcName = npcs[0]?.npc_name;
  assert(npcName, 'quest_npc.json should contain an NPC');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const npcKey = `quest_npc_npc_${npcName}`;
  const questKey = `quest_npc_quest_${npcName}_1`;
  const contentKey = `quest_npc_content_${npcName}_1_0`;
  const unrelatedKey = 'df5_unrelated_probe';

  try {
    await page.goto(`${BASE}/zh-Hans/quest_npc/`, {
      waitUntil: 'domcontentloaded',
      timeout: 20000,
    });
    await page.locator('#root').waitFor({ state: 'visible', timeout: 20000 });

    const seed = (args) => {
      localStorage.setItem('quest_npc_season', String(args.season));
      localStorage.setItem(args.npc, '1');
      localStorage.setItem(args.quest, '1');
      localStorage.setItem(args.content, '1');
      localStorage.setItem(args.unrelated, 'keep');
    };
    const keys = {
      season: SEASON,
      npc: npcKey,
      quest: questKey,
      content: contentKey,
      unrelated: unrelatedKey,
    };
    await page.evaluate(seed, keys);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('#root').waitFor({ state: 'visible', timeout: 20000 });

    const checkbox = page
      .locator(`a[href$="/quest_npc/${npcName}"]`)
      .locator('..')
      .locator('input[type="checkbox"]');
    await checkbox.waitFor({ state: 'visible', timeout: 20000 });
    assert.equal(
      await checkbox.isChecked(),
      true,
      'seeded progress should render'
    );

    const clearButton = page.getByRole('button', {
      name: '清空本赛季任务进度',
    });
    await clearButton.waitFor({ state: 'visible', timeout: 20000 });

    await clearButton.click();
    const dialog = page.getByRole('dialog');
    await dialog.waitFor({ state: 'visible', timeout: 10000 });
    await dialog.getByRole('button', { name: /取\s*消/ }).click();
    await dialog.waitFor({ state: 'hidden', timeout: 10000 });
    assert.deepEqual(
      await page.evaluate(
        ([npc, quest, content, unrelated]) => [
          localStorage.getItem('quest_npc_season'),
          localStorage.getItem(npc),
          localStorage.getItem(quest),
          localStorage.getItem(content),
          localStorage.getItem(unrelated),
        ],
        [npcKey, questKey, contentKey, unrelatedKey]
      ),
      [String(SEASON), '1', '1', '1', 'keep'],
      'cancel must keep every saved mark'
    );

    await clearButton.click();
    await dialog.waitFor({ state: 'visible', timeout: 10000 });
    await dialog.getByRole('button', { name: /确\s*认\s*清\s*空/ }).click();
    await dialog.waitFor({ state: 'hidden', timeout: 10000 });

    assert.deepEqual(
      await page.evaluate(
        ([npc, quest, content, unrelated]) => [
          localStorage.getItem('quest_npc_season'),
          localStorage.getItem(npc),
          localStorage.getItem(quest),
          localStorage.getItem(content),
          localStorage.getItem(unrelated),
        ],
        [npcKey, questKey, contentKey, unrelatedKey]
      ),
      [String(SEASON), null, null, null, 'keep'],
      'confirm must clear task marks and keep unrelated settings'
    );
    await page.waitForFunction(
      (selector) => {
        const link = document.querySelector(selector);
        const input = link?.parentElement?.querySelector(
          'input[type="checkbox"]'
        );
        return input && !input.checked;
      },
      `a[href$="/quest_npc/${npcName}"]`,
      { timeout: 10000 }
    );

    await page.evaluate(
      ({ npc, quest, content, unrelated }) => {
        localStorage.setItem('quest_npc_season', '10');
        localStorage.setItem(npc, '1');
        localStorage.setItem(quest, '1');
        localStorage.setItem(content, '1');
        localStorage.setItem(unrelated, 'keep');
      },
      {
        npc: npcKey,
        quest: questKey,
        content: contentKey,
        unrelated: unrelatedKey,
      }
    );
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('#root').waitFor({ state: 'visible', timeout: 20000 });
    await page.waitForFunction(
      (npc) =>
        localStorage.getItem('quest_npc_season') === '11' &&
        localStorage.getItem(npc) === null,
      npcKey,
      { timeout: 10000 }
    );

    console.log(
      'PASS quest season reset, manual clear, and season 11 metadata'
    );
  } finally {
    await context.close();
    await browser.close();
  }
}

await main();
