import { DEFAULT_LANG, type LocaleDict } from './locale';
import {
  buildSeoDescription,
  type SeoFacts,
  type SeoPageType,
} from './seoTemplate.mjs';
import { ssrLocalizedDescription } from './ssrTitle';

export { buildSeoDescription, type SeoFacts, type SeoPageType };

export function localizedSeoDescription(
  lang: string,
  dict: LocaleDict | null,
  type: SeoPageType,
  facts?: SeoFacts
): string {
  if (lang !== DEFAULT_LANG && !dict) {
    return ssrLocalizedDescription() ?? buildSeoDescription(lang, type, facts);
  }
  return buildSeoDescription(lang, type, facts);
}
