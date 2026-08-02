import { useEffect, useMemo, useState } from 'react';
import { useDataVersion } from '../hooks/useDataVersion';
import { useSSRData } from '../context/SSRDataContext';
import {
  DEFAULT_LANG,
  loadLocale,
  type LocaleDict,
  type SupportedLang,
} from './locale';
import { useLanguage } from './LanguageContext';
import { uiDict } from './uiLocale';

export function useLocale() {
  const { lang } = useLanguage();
  const dataVersion = useDataVersion();
  const ssrDict = useSSRData<LocaleDict>('__locale');
  const [dict, setDict] = useState<LocaleDict | null>(() => ssrDict);
  const [loadedLang, setLoadedLang] = useState<SupportedLang | null>(() =>
    ssrDict ? lang : null
  );

  useEffect(() => {
    if (lang === DEFAULT_LANG) {
      setDict(null);
      setLoadedLang(DEFAULT_LANG);
      return;
    }
    if (loadedLang === lang) return;
    setDict(null);
    setLoadedLang(null);
    if (!dataVersion) return;
    let cancelled = false;
    loadLocale(dataVersion, lang)
      .then((localeDict) => {
        if (cancelled) return;
        setDict(localeDict);
        setLoadedLang(lang);
      })
      .catch(() => {
        if (cancelled) return;
        setDict(null);
        setLoadedLang(lang);
      });
    return () => {
      cancelled = true;
    };
  }, [dataVersion, lang, loadedLang]);

  const activeDict = lang === DEFAULT_LANG || loadedLang !== lang ? null : dict;
  const localeReady = lang === DEFAULT_LANG || loadedLang === lang;

  const mergedDict = useMemo(() => {
    const ui = uiDict(lang);
    if (!activeDict) return ui;
    return { ...activeDict, ...ui };
  }, [activeDict, lang]);

  const t = (key: string | undefined, fallback: string) => {
    if (!key) return fallback;
    return mergedDict[key] ?? fallback;
  };

  const ut = (key: string) => {
    return mergedDict[key] ?? key;
  };

  return { lang, dict: activeDict, localeReady, t, ut };
}
