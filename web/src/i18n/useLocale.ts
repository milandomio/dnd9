import { useEffect, useState } from 'react';
import { useDataVersion } from '../hooks/useDataVersion';
import { DEFAULT_LANG, loadLocale, type LocaleDict } from './locale';
import { useLanguage } from './LanguageContext';

export function useLocale() {
  const { lang } = useLanguage();
  const dataVersion = useDataVersion();
  const [dict, setDict] = useState<LocaleDict | null>(null);

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

  const t = (key: string | undefined, fallback: string) => {
    if (!dict || !key) return fallback;
    return dict[key] || fallback;
  };

  return { lang, dict, t };
}
