export type SeoPageType =
  | 'home'
  | 'list'
  | 'entity'
  | 'lootdrop'
  | 'explore'
  | 'questItems'
  | 'questGroup'
  | 'questNpcs'
  | 'questNpc'
  | 'modules'
  | 'moduleGroup'
  | 'module';

export type SeoFacts = Record<string, string | number | undefined>;

export function buildSeoDescription(
  lang: string,
  type: SeoPageType,
  facts?: SeoFacts
): string;
