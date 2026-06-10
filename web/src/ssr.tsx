/**
 * SSR entry – called by the SSG build script.
 *
 * Renders a React route to HTML string + head tags
 * using renderToString + StaticRouter.
 *
 * NOTE: Ant Design v5 accesses browser globals (document, window)
 * during rendering. We stub them here so renderToString works in Node.
 */
import {} from 'react';
import { renderToString } from 'react-dom/server';
import { StaticRouter } from 'react-router-dom/server';
import { HelmetProvider } from 'react-helmet-async';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider } from './hooks/useTheme';
import { DebugProvider } from './hooks/useDebug';
import SSRDataContext from './context/SSRDataContext';
import { AppInner } from './App';

// Ant Design v5+ requires browser-global stubs for SSR
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).window = globalThis;
const styleEl = {
  className: '',
  setAttribute: () => {},
  removeAttribute: () => {},
  insertAdjacentElement: () => null,
  textContent: '',
  sheet: { cssRules: [], insertRule: () => {}, removeRule: () => {} },
  parentNode: { removeChild: () => {} },
  appendChild: () => {},
  insertBefore: () => {},
};

globalThis.document = {
  createElement: (tag: string) => {
    if (tag === 'style') return { ...styleEl, tagName: 'STYLE' };
    if (tag === 'meta') return { ...styleEl, tagName: 'META' };
    if (tag === 'link') return { ...styleEl, tagName: 'LINK' };
    return {
      className: '',
      style: {},
      setAttribute: () => {},
      removeAttribute: () => {},
      appendChild: () => {},
      insertAdjacentElement: () => null,
      textContent: '',
      parentNode: { removeChild: () => {} },
    };
  },
  createTextNode: () => ({}),
  getElementsByTagName: () => [],
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: { style: {} },
  head: {
    appendChild: () => {},
    querySelectorAll: () => [],
    insertBefore: () => {},
  },
  body: { appendChild: () => {}, removeChild: () => {} },
} as any;
globalThis.navigator = { userAgent: 'node' } as any;
globalThis.location = { href: '', pathname: '', search: '', hash: '' } as any;
globalThis.getComputedStyle = () => ({}) as CSSStyleDeclaration;

export function render(url: string, ssrDataMap: Record<string, any>) {
  const helmetContext = { helmet: {} } as any;

  const html = renderToString(
    <HelmetProvider context={helmetContext}>
      <ThemeProvider>
        <ConfigProvider
          locale={zhCN}
          theme={{
            algorithm: theme.darkAlgorithm,
            token: { colorPrimary: '#1677ff' },
          }}
        >
          <DebugProvider>
            <SSRDataContext.Provider value={ssrDataMap}>
              <StaticRouter location={url}>
                <AppInner />
              </StaticRouter>
            </SSRDataContext.Provider>
          </DebugProvider>
        </ConfigProvider>
      </ThemeProvider>
    </HelmetProvider>
  );

  const { helmet } = helmetContext;

  return {
    html,
    head: [helmet?.title?.toString() ?? '', helmet?.meta?.toString() ?? '']
      .join('')
      .trim(),
  };
}
