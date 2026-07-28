import type { ReactNode } from 'react';
import { createContext, useContext, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { DEFAULT_LANG, isSupportedLang, type SupportedLang } from './locale';

type LanguageContextValue = {
  lang: SupportedLang;
  hasLangPrefix: boolean;
  stripLangPrefix: (path: string) => string;
  withLangPrefix: (path: string, nextLang: SupportedLang) => string;
};

export function stripLangPrefix(path: string) {
  const parts = path.split('/').filter(Boolean);
  if (parts.length > 0 && isSupportedLang(parts[0])) {
    const stripped = `/${parts.slice(1).join('/')}`;
    return stripped === '/' || stripped === '' ? '/' : stripped;
  }
  return path || '/';
}

export function withLangPrefix(path: string, nextLang: SupportedLang) {
  const stripped = stripLangPrefix(path);
  return `/${nextLang}${stripped === '/' ? '/' : stripped}`;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: DEFAULT_LANG,
  hasLangPrefix: false,
  stripLangPrefix,
  withLangPrefix,
});

function initialRenderedLang(routeLang: SupportedLang): SupportedLang {
  if (typeof window === 'undefined') return routeLang;
  const ssrData = (
    window as typeof window & {
      __SSR_DATA__?: { __ssrLang?: string };
    }
  ).__SSR_DATA__;
  return isSupportedLang(ssrData?.__ssrLang) ? ssrData.__ssrLang : routeLang;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const routeSegment = location.pathname.split('/').filter(Boolean)[0];
  const hasLangPrefix = isSupportedLang(routeSegment);
  const routeLang = hasLangPrefix ? routeSegment : DEFAULT_LANG;
  const [lang, setLang] = useState(() => initialRenderedLang(routeLang));

  useEffect(() => {
    setLang(routeLang);
  }, [routeLang]);

  return (
    <LanguageContext.Provider
      value={{
        lang,
        hasLangPrefix,
        stripLangPrefix,
        withLangPrefix: (path, nextLang) =>
          withLangPrefix(path || location.pathname, nextLang),
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
