import type { Locale } from 'antd/es/locale';
import { useEffect, useState } from 'react';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import deDE from 'antd/locale/de_DE';
import esES from 'antd/locale/es_ES';
import frFR from 'antd/locale/fr_FR';
import jaJP from 'antd/locale/ja_JP';
import koKR from 'antd/locale/ko_KR';
import ptBR from 'antd/locale/pt_BR';
import ruRU from 'antd/locale/ru_RU';
import zhTW from 'antd/locale/zh_TW';
import { type SupportedLang } from './locale';
import { useLanguage } from './LanguageContext';

const ANTD_LOCALE_MAP: Record<SupportedLang, Locale> = {
  'zh-Hans': zhCN,
  en: enUS,
  de: deDE,
  es: esES,
  fr: frFR,
  ja: jaJP,
  ko: koKR,
  'pt-BR': ptBR,
  ru: ruRU,
  'zh-Hant': zhTW,
};

export function useAntdLocale(): Locale {
  const { lang } = useLanguage();
  const [locale, setLocale] = useState<Locale>(ANTD_LOCALE_MAP[lang] ?? zhCN);

  useEffect(() => {
    setLocale(ANTD_LOCALE_MAP[lang] ?? zhCN);
  }, [lang]);

  return locale;
}
