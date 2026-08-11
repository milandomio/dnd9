import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://localhost:8080';

function isRecognitionResource(url) {
  const normalized = url.toLowerCase();
  return (
    normalized.includes('opencv') ||
    normalized.includes('mapimagerecognition') ||
    normalized.endsWith('.wasm')
  );
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const recognitionRequests = [];

  page.on('request', (request) => {
    if (isRecognitionResource(request.url()))
      recognitionRequests.push(request.url());
  });

  try {
    await page.goto(`${BASE}/zh-Hans/items/Ale/`, {
      waitUntil: 'domcontentloaded',
      timeout: 20000,
    });
    await page.locator('#root').waitFor({ state: 'visible', timeout: 20000 });

    await page.getByRole('button', { name: '显示调试信息' }).click();
    const toggle = page.getByRole('checkbox', { name: '地图截图识别' });
    await toggle.click();
    const consentDialog = page.getByRole('dialog');
    await consentDialog.waitFor({ state: 'visible' });

    const consentText = await consentDialog.innerText();
    if (
      !consentText.includes(
        '请确认你在PVE模式使用，越来越黑暗闪电指南 DarkFlashNav 不支持你在其他模式使用。'
      )
    ) {
      throw new Error(`unexpected consent text: ${consentText}`);
    }

    const requestsBeforeCancel = recognitionRequests.length;
    await consentDialog.getByRole('button', { name: /取\s*消/ }).click();
    if (await toggle.isChecked()) throw new Error('cancel enabled recognition');
    if (recognitionRequests.length !== requestsBeforeCancel) {
      throw new Error(
        'recognition resources loaded after consent was cancelled'
      );
    }

    await toggle.click();
    await consentDialog.waitFor({ state: 'visible' });
    await consentDialog.getByRole('button', { name: '同意并继续' }).click();
    await page
      .getByText('截图识图', { exact: true })
      .waitFor({ state: 'visible' });
    if (!(await toggle.isChecked()))
      throw new Error('consent did not enable recognition');

    await toggle.click();
    await toggle.click();
    await consentDialog.waitFor({ state: 'visible' });

    console.log(
      `PASS map recognition consent: ${recognitionRequests.length} recognition resource requests after agreement`
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error('FAIL map recognition consent:', error.message);
  process.exit(1);
});
