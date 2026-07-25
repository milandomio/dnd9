import type { ReactNode } from 'react';
import { createContext, useContext } from 'react';
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

export function LanguageProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const routeLang = location.pathname.split('/').filter(Boolean)[0];
  const hasLangPrefix = isSupportedLang(routeLang);
  const lang = hasLangPrefix ? routeLang : DEFAULT_LANG;

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
