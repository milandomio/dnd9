/** Data-side drop_rates keys (zh labels in JSON) → Game.json translation_key */
export const DROP_RATE_MODE_TRANSLATION_KEY: Record<string, string> = {
  PVE: 'Text_Code_DCPartyFinderCreateWidget_FilterModePvE',
  普通: 'Text_Code_DCPartyFinderCreateWidget_FilterModeNormal',
  豪客赛: 'Text_Code_DCPartyFinderCreateWidget_FilterModeHighRoller',
  逆袭赛: 'Text_Code_DCPartyFinderCreateWidget_FilterModeSquireRoyale',
};

/** UI fallback when locale dict has no Game.json key yet */
export const DROP_RATE_MODE_UI_KEY: Record<string, string> = {
  PVE: 'ui.filter.pve',
  普通: 'ui.filter.normal',
  豪客赛: 'ui.filter.high_roller',
  逆袭赛: 'ui.filter.counter_raid',
};

export type LocaleT = (key: string | undefined, fallback: string) => string;
export type LocaleUt = (key: string) => string;

/**
 * Localize drop-rate mode: look up Game.json key via locale dict,
 * then ui.filter.* fallback, then raw data key (中文).
 */
export function dropRateModeLabel(
  mode: string,
  t: LocaleT,
  ut: LocaleUt
): string {
  const tk = DROP_RATE_MODE_TRANSLATION_KEY[mode];
  if (tk) {
    const fromLocale = t(tk, '');
    if (fromLocale) return fromLocale;
  }
  const ui = DROP_RATE_MODE_UI_KEY[mode];
  if (ui) {
    const fromUi = ut(ui);
    if (fromUi && fromUi !== ui) return fromUi;
  }
  return mode;
}

export interface DropRateEntry {
  translation: string;
  translation_key?: string;
  spawn_rate: number;
  spawn_rates?: Record<string, number>;
  drop_rates: Record<string, number>;
}

export function filterDropRates(
  drop_rates: Record<string, number>,
  modeFilter?: string
): [string, number][] {
  return Object.entries(drop_rates).filter(
    ([k]) => !modeFilter || k === modeFilter
  );
}

/** Build `[Mode:rate%]` or `[Mode:spawn%×rate%]` with i18n mode labels */
export function formatDropRateModeSegments(
  drop_rates: Record<string, number>,
  t: LocaleT,
  ut: LocaleUt,
  opts?: {
    modeFilter?: string;
    spawn_rates?: Record<string, number>;
    adjSpawnRate?: (v: number) => number;
  }
): string {
  const adj = opts?.adjSpawnRate ?? ((v: number) => v);
  const multi =
    opts?.spawn_rates && Object.keys(opts.spawn_rates).length > 1
      ? opts.spawn_rates
      : undefined;

  return filterDropRates(drop_rates, opts?.modeFilter)
    .map(([mode, rate]) => {
      const label = dropRateModeLabel(mode, t, ut);
      if (multi) {
        const sRate = multi[mode];
        return sRate != null
          ? `[${label}:${adj(sRate)}%×${rate}%]`
          : `[${label}:${rate}%]`;
      }
      return `[${label}:${rate}%]`;
    })
    .join('');
}

/** Full rate suffix after entity name */
export function formatDropRateSuffix(
  entry: DropRateEntry,
  t: LocaleT,
  ut: LocaleUt,
  opts?: {
    modeFilter?: string;
    adjSpawnRate?: (v: number) => number;
    parenModes?: boolean;
  }
): string {
  const adj = opts?.adjSpawnRate ?? ((v: number) => v);
  const multi =
    !!entry.spawn_rates && Object.keys(entry.spawn_rates).length > 1;

  if (multi) {
    return formatDropRateModeSegments(entry.drop_rates, t, ut, {
      modeFilter: opts?.modeFilter,
      spawn_rates: entry.spawn_rates,
      adjSpawnRate: adj,
    });
  }

  const spawnStr = `${adj(entry.spawn_rate)}%`;
  const modes = formatDropRateModeSegments(entry.drop_rates, t, ut, {
    modeFilter: opts?.modeFilter,
  });
  if (!modes) return spawnStr;
  if (opts?.parenModes) return `${spawnStr}(${modes})`;
  return `${spawnStr}${modes}`;
}
