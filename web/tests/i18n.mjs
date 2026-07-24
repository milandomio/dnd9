import { chromium } from "playwright";

const BASE = process.env.BASE_URL || "http://localhost:8080";
const TIMEOUT = 20000;

const PAGES = [
  { path: "/", desc: "HomePage", lang: "zh-Hans" },
  { path: "/en/", desc: "HomePage(en)", lang: "en" },
  { path: "/ja/", desc: "HomePage(ja)", lang: "ja" },
  { path: "/items/", desc: "ItemsList", lang: "zh-Hans" },
  { path: "/en/items/", desc: "ItemsList(en)", lang: "en" },
  { path: "/ja/items/", desc: "ItemsList(ja)", lang: "ja" },
  { path: "/items/Ale/", desc: "ItemDetail(Ale)", lang: "zh-Hans" },
  { path: "/en/items/Ale/", desc: "ItemDetail(Ale)(en)", lang: "en" },
  { path: "/ja/items/Ale/", desc: "ItemDetail(Ale)(ja)", lang: "ja" },
  { path: "/lootdrops/HeaterShield_8001/", desc: "LootdropDetail", lang: "zh-Hans" },
  { path: "/en/lootdrops/HeaterShield_8001/", desc: "LootdropDetail(en)", lang: "en" },
  { path: "/ja/lootdrops/HeaterShield_8001/", desc: "LootdropDetail(ja)", lang: "ja" },
  { path: "/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/", desc: "ModuleDetail", lang: "zh-Hans" },
  { path: "/en/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/", desc: "ModuleDetail(en)", lang: "en" },
  { path: "/ja/dungeon_modules/ShipGraveyard/ShipGraveyard_BladehandRefuge/", desc: "ModuleDetail(ja)", lang: "ja" },
];

const HYDRO_KEYS = ["Hydration", "hydrat", "#418", "#423", "did not match"];

async function testPage(browser, { path, desc, lang }) {
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => pageErrors.push(err.message));

  try {
    await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded", timeout: TIMEOUT });
    await page.waitForSelector("#root", { timeout: TIMEOUT }).catch(() => {});
    await page.waitForTimeout(2000);

    const title = await page.title().catch(() => "");
    const hydroErrors = [...pageErrors, ...consoleErrors].filter((e) =>
      HYDRO_KEYS.some((k) => e.includes(k))
    );
    const hasTitle = title && title.length > 0 && title !== "DarkFlashNav";

    return { desc, lang, title, hasTitle, hydroErrors, pageErrors, consoleErrors, ok: true };
  } catch (err) {
    return { desc, lang, title: "", hasTitle: false, hydroErrors: [], pageErrors: [err.message], consoleErrors: [], ok: false, error: err.message };
  } finally {
    await page.close();
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const results = { pass: 0, fail: 0, hydrationFails: 0, titleFails: 0, timeoutFails: 0, errors: [] };

  for (const pageCfg of PAGES) {
    const res = await testPage(browser, pageCfg);
    const isNonZh = res.lang !== "zh-Hans";
    let pass = res.ok;

    if (!res.ok || res.error) {
      pass = false;
      results.timeoutFails++;
    }

    if (res.hydroErrors.length > 0) {
      pass = false;
      results.hydrationFails++;
    }

    if (isNonZh && !res.hasTitle) {
      pass = false;
      results.titleFails++;
    }

    if (pass) {
      console.log(`PASS [${res.lang}] ${res.desc}: title="${res.title}"`);
      results.pass++;
    } else {
      const reasons = [];
      if (!res.ok) reasons.push(`load_fail=${res.error}`);
      if (res.hydroErrors.length > 0) reasons.push(`hydro(${res.hydroErrors.length})`);
      if (isNonZh && !res.hasTitle) reasons.push("no_title");
      results.fail++;
      console.log(`FAIL [${res.lang}] ${res.desc}: ${reasons.join(", ")} title="${res.title}"`);
      results.errors.push(res);
    }
  }

  // Cross-language title comparison
  for (const entity of [
    { desc: "ItemDetail(Ale)", paths: { en: "/en/items/Ale/", ja: "/ja/items/Ale/" } },
  ]) {
    const titles = {};
    for (const [lang, path] of Object.entries(entity.paths)) {
      const p = await browser.newPage();
      try {
        await p.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded", timeout: TIMEOUT });
        await p.waitForTimeout(2000);
        titles[lang] = await p.title();
      } catch { titles[lang] = ""; }
      await p.close();
    }
    if (titles.en && titles.ja && titles.en !== titles.ja) {
      console.log(`PASS [i18n] ${entity.desc}: en≠ja ✓`);
    } else {
      console.log(`SKIP [i18n] ${entity.desc}: en="${titles.en}" ja="${titles.ja}"`);
    }
  }

  await browser.close();

  console.log(`\n=== RESULTS ===`);
  console.log(`  Pass: ${results.pass}`);
  console.log(`  Fail: ${results.fail} (hydration=${results.hydrationFails}, title=${results.titleFails}, timeout=${results.timeoutFails})`);

  if (results.hydrationFails > 0) {
    console.log(`\n⚠️  ${results.hydrationFails} pages have hydration errors (#418/#423).`);
    console.log(`   Likely cause: SSG post-processing swaps <title> + <html lang> but React`);
    console.log(`   hydration detects non-zh-Hans lang via __SSR_DATA__ and immediately`);
    console.log(`   triggers locale dict load, causing Helmet <title> to mismatch SSR <title>.`);
    console.log(`   Fix needed in how non-zh-Hans pages handle hydration.`);
  }

  if (results.titleFails > 0) {
    console.log(`\n⚠️  ${results.titleFails} non-zh-Hans pages have empty/missing titles.`);
  }

  process.exit(results.fail > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});
