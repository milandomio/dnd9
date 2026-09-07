import { useEffect } from 'react';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';

const GOOGLE_TAG_ID = 'G-0SHM5GPXYN';
const CLOUDFLARE_BEACON_ID = 'cloudflare-web-analytics-beacon';
const GOOGLE_TAG_SCRIPT_ID = 'google-gtag-script';
const CLOUDFLARE_BEACON_TOKEN = 'e6b67148ae564d73a2e02b4d199da387';

type AnalyticsWindow = Window & {
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
  gtagInitialized?: boolean;
};

export default function Footer() {
  const { tokens } = useTheme();
  const { ut } = useLocale();

  useEffect(() => {
    const analyticsWindow = window as AnalyticsWindow;
    analyticsWindow.dataLayer = analyticsWindow.dataLayer || [];
    analyticsWindow.gtag =
      analyticsWindow.gtag ||
      function gtag(...args: unknown[]) {
        analyticsWindow.dataLayer?.push(args);
      };
    if (!analyticsWindow.gtagInitialized) {
      analyticsWindow.gtag('js', new Date());
      analyticsWindow.gtag('config', GOOGLE_TAG_ID);
      analyticsWindow.gtagInitialized = true;
    }

    if (!document.getElementById(GOOGLE_TAG_SCRIPT_ID)) {
      const googleScript = document.createElement('script');
      googleScript.id = GOOGLE_TAG_SCRIPT_ID;
      googleScript.async = true;
      googleScript.src = `https://www.googletagmanager.com/gtag/js?id=${GOOGLE_TAG_ID}`;
      document.body.appendChild(googleScript);
    }

    if (!document.getElementById(CLOUDFLARE_BEACON_ID)) {
      const cloudflareScript = document.createElement('script');
      cloudflareScript.id = CLOUDFLARE_BEACON_ID;
      cloudflareScript.async = true;
      cloudflareScript.src =
        'https://static.cloudflareinsights.com/beacon.min.js';
      cloudflareScript.dataset.cfBeacon = JSON.stringify({
        token: CLOUDFLARE_BEACON_TOKEN,
      });
      document.body.appendChild(cloudflareScript);
    }
  }, []);

  return (
    <footer
      style={{
        marginTop: 24,
        padding: '12px 0 0',
        textAlign: 'center',
        fontSize: 13,
        color: tokens.muted,
        borderTop: `1px solid ${tokens.border}`,
      }}
    >
      <p style={{ margin: 0 }}>
        © 2026{' '}
        <a
          href="https://www.bilibili.com/video/BV1hoR7BzExq"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          @milando
        </a>
        {' · '}
        <a
          href="https://darkanddarker.wiki.spellsandguns.com/Dark_and_Darker_Wiki"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          WIKI
        </a>
        {' · '}
        <a
          href="https://chatglm.cn/main/alltoolsdetail?lang=en"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          ChatGLM
        </a>
        {' · '}
        <a
          href="https://platform.deepseek.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          DeepSeek
        </a>
        {' · '}
        <a
          href="https://github.com/features/actions"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          GitHub
        </a>
        {' · '}
        <a
          href="https://pages.cloudflare.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          Cloudflare
        </a>
      </p>
      <p style={{ margin: '4px 0 0' }}>
        {ut('ui.footer.attribution')}{' '}
        <a
          href="https://darkanddarker.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          Dark and Darker
        </a>
      </p>
    </footer>
  );
}
