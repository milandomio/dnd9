import { useEffect, useMemo, useState } from 'react';
import { useDataVersion } from '../hooks/useDataVersion';
import { useSSRData } from '../context/SSRDataContext';
import { DEFAULT_LANG, loadLocale, type LocaleDict } from './locale';
import { useLanguage } from './LanguageContext';
import { uiDict } from './uiLocale';

export function useLocale() {
  const { lang } = useLanguage();
  const dataVersion = useDataVersion();
  const ssrDict = useSSRData<LocaleDict>('__locale');
  const [dict, setDict] = useState<LocaleDict | null>(() => ssrDict);

  useEffect(() => {
    if (lang === DEFAULT_LANG) {
      setDict(null);
      return;
    }
    if (!dataVersion) return;
    let cancelled = false;
    loadLocale(dataVersion, lang)
      .then((localeDict) => {
        if (!cancelled) setDict(localeDict);
      })
      .catch(() => {
        if (!cancelled) setDict(null);
      });
    return () => {
      cancelled = true;
    };
  }, [dataVersion, lang]);

  const mergedDict = useMemo(() => {
    const ui = uiDict(lang);
    if (!dict) return ui;
    return { ...dict, ...ui };
  }, [dict, lang]);

  const t = (key: string | undefined, fallback: string) => {
    if (!key) return fallback;
    return mergedDict[key] ?? fallback;
  };

  const ut = (key: string) => {
    return mergedDict[key] ?? key;
  };

  return { lang, dict, t, ut };
}
