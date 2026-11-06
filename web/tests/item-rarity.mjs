import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8081';
const ITEMS = ['Torch', 'Lantern'];

const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 },
  });

  for (const itemName of ITEMS) {
    await page.goto(BASE_URL + '/zh-Hans/items/' + itemName + '/', {
      waitUntil: 'domcontentloaded',
    });

    const rarityGroup = page.getByRole('group', { name: '稀有度' });
    await rarityGroup.waitFor({ state: 'visible' });
    const links = rarityGroup.locator('a');
    assert.equal(
      await links.count(),
      7,
      itemName + ' should expose 7 rarities'
    );
    const linkMetrics = await links.evaluateAll((elements) =>
      elements.map((element) => ({
        height: element.getBoundingClientRect().height,
        opacity: getComputedStyle(element).opacity,
      }))
    );
    assert.ok(
      linkMetrics.every(
        ({ height, opacity }) => height >= 44 && opacity === '1'
      ),
      itemName + ' overview rarity links should remain readable touch targets'
    );
    assert.equal(
      await rarityGroup.locator('a[aria-current="page"]').count(),
      0,
      itemName + ' overview must not select a specific rarity'
    );

    const epicLink = rarityGroup.locator(
      'a[href="/zh-Hans/lootdrops/' + itemName + '_5001/"]'
    );
    await epicLink.waitFor({ state: 'visible' });
    const epicLabel = await epicLink.innerText();
    await epicLink.click();
    await page.waitForURL('**/zh-Hans/lootdrops/' + itemName + '_5001/');
    await page
      .getByText(/\d+(?:\.\d+)?%/)
      .first()
      .waitFor({ state: 'visible' });

    const selectedRarityLink = page
      .locator('a[aria-current="page"]')
      .filter({ hasText: epicLabel });
    assert.equal(
      await selectedRarityLink.count(),
      1,
      itemName + ' rarity page should mark its selected rarity'
    );
    assert.equal(
      await selectedRarityLink.getAttribute('href'),
      '/zh-Hans/lootdrops/' + itemName + '_5001/',
      itemName + ' should select the clicked rarity'
    );
    assert.match(
      await page.locator('body').innerText(),
      /\d+(?:\.\d+)?%/,
      itemName + ' rarity page should show drop rates'
    );
  }

  console.log('Torch and Lantern rarity navigation verified.');
} finally {
  await browser.close();
}
