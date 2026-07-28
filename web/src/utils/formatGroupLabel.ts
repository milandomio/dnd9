/** Build i18n dungeon group label from key fields, with Chinese group_display fallback. */

export interface GroupLabelSource {
  group?: string;
  group_key?: string;
  group_floor?: number;
  group_sub_key?: string | null;
  group_display?: string;
}

type TFn = (key: string | undefined, fallback: string) => string;
type UtFn = (key: string) => string;

export function formatGroupLabel(
  src: GroupLabelSource | null | undefined,
  t: TFn,
  ut: UtFn
): string {
  if (!src) return ut('ui.common.ungrouped');
  const key = src.group_key;
  if (key) {
    const base = t(key, '');
    if (base) {
      const floor = src.group_floor ?? 1;
      const floorSuffix = ut('ui.common.floor');
      const subKey = src.group_sub_key;
      if (subKey) {
        const sub = t(subKey, '');
        if (sub) return `${base}${floor}${floorSuffix}（${sub}）`;
      }
      return `${base}${floor}${floorSuffix}`;
    }
  }
  return src.group_display || src.group || ut('ui.common.ungrouped');
}
