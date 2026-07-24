import type { Locale } from 'antd/es/locale';
import { useEffect, useState } from 'react';
import zhCN from 'antd/locale/zh_CN';
import { type SupportedLang } from './locale';
import { useLanguage } from './LanguageContext';

const ANTD_LOCALE_MAP: Record<
  SupportedLang,
  () => Promise<{ default: Locale }>
> = {
  'zh-Hans': () => import('antd/locale/zh_CN'),
  en: () => import('antd/locale/en_US'),
  de: () => import('antd/locale/de_DE'),
  es: () => import('antd/locale/es_ES'),
  fr: () => import('antd/locale/fr_FR'),
  ja: () => import('antd/locale/ja_JP'),
  ko: () => import('antd/locale/ko_KR'),
  'pt-BR': () => import('antd/locale/pt_BR'),
  ru: () => import('antd/locale/ru_RU'),
  'zh-Hant': () => import('antd/locale/zh_TW'),
};

export function useAntdLocale(): Locale {
  const { lang } = useLanguage();
  const [locale, setLocale] = useState<Locale>(zhCN);

  useEffect(() => {
    if (lang === 'zh-Hans') {
      setLocale(zhCN);
      return;
    }
    let cancelled = false;
    ANTD_LOCALE_MAP[lang]()
      .then((mod) => {
        if (!cancelled) setLocale(mod.default);
      })
      .catch(() => {
        if (!cancelled) setLocale(zhCN);
      });
    return () => {
      cancelled = true;
    };
  }, [lang]);

  return locale;
}
