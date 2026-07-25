import { dataUrl } from '../utils/dataUrl';

export const DEFAULT_LANG = 'zh-Hans';

export const SUPPORTED_LANGS = [
  'zh-Hans',
  'en',
  'de',
  'es',
  'fr',
  'ja',
  'ko',
  'pt-BR',
  'ru',
  'zh-Hant',
] as const;

export type SupportedLang = (typeof SUPPORTED_LANGS)[number];

export const LANG_DISPLAY_NAME: Record<SupportedLang, string> = {
  'zh-Hans': '简体中文',
  en: 'English',
  de: 'Deutsch',
  es: 'Español',
  fr: 'Français',
  ja: '日本語',
  ko: '한국어',
  'pt-BR': 'Português (BR)',
  ru: 'Русский',
  'zh-Hant': '繁體中文',
};

export type LocaleDict = Record<string, string>;

const cache = new Map<string, Promise<LocaleDict>>();

export function isSupportedLang(
  lang: string | undefined
): lang is SupportedLang {
  return !!lang && SUPPORTED_LANGS.includes(lang as SupportedLang);
}

export function localeUrl(version: string, lang: SupportedLang) {
  return dataUrl(version, `/data/json/locale/${lang}.json`);
}

export function loadLocale(version: string, lang: SupportedLang) {
  const key = `${version}:${lang}`;
  const cached = cache.get(key);
  if (cached) return cached;

  const promise = fetch(localeUrl(version, lang)).then((r) => {
    if (!r.ok) throw new Error(`Failed to load locale ${lang}: ${r.status}`);
    return r.json() as Promise<LocaleDict>;
  });
  cache.set(key, promise);
  return promise;
}

export function translate(
  dict: LocaleDict | null,
  key: string | undefined,
  fallback: string
) {
  if (!dict || !key) return fallback;
  return dict[key] || fallback;
}
