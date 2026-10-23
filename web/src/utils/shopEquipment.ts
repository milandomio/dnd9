import type { ShopItem } from '../types/data';

/** Equipment gear families, in the order the shop page lists them. */
export interface EquipmentCategoryGroup {
  /** Game translation key (空串表示未知类别). */
  category_key: string;
  /** Already-translated label, used when the locale has no dictionary entry. */
  label: string;
  /** Sum of the chances of every item in this category (0-1). */
  cumulative: number;
  /** Shared shop price, or 0 when the entries disagree (then it is hidden). */
  price: number;
  currency: string;
  items: ShopItem[];
}

export interface EquipmentGroup {
  /** `mini_artifact` for the special 10-item batch, else `tier`. */
  pool: 'tier' | 'mini_artifact';
  /** Raw rarity enum (drives the card/palette colour). */
  rarity: string;
  /** Game translation key for the rarity (unique -> 独特). */
  rarity_key: string;
  /** Already-translated rarity label (zh-Hans ships it in the payload). */
  rarity_label: string;
  /** Chance of one item in this group (0-1). */
  chance: number;
  /** Sum of every item chance in this group (0-1). */
  cumulative: number;
  /** Shared shop price, or 0 when the entries disagree. */
  price: number;
  currency: string;
  /** Second grouping level: 饰品 / 护甲 / 武器 (empty for minor artifacts). */
  categories: EquipmentCategoryGroup[];
  items: ShopItem[];
}

/** The value every entry shares, or a zero value when they disagree. */
function uniform<T>(
  items: ShopItem[],
  read: (item: ShopItem) => T,
  empty: T
): T {
  const first = read(items[0]);
  return items.every((item) => read(item) === first) ? first : empty;
}

/**
 * Group equipment entries that share the same roll weight.
 *
 * The equipment slot is a weighted pool: every rarity band has one weight, so
 * all entries of a band share one chance. The band's cumulative chance — the sum
 * over its entries — is what a player actually cares about, and within a band
 * every 饰品 / 护甲 / 武器 entry also costs the same, so one summary line per
 * category carries both the odds and the price.
 *
 * The 10 minor artifacts (Bloodbound 血缚 ...) share a weight of their own in the
 * game's stock table, so they form a separate group even though their quality is
 * Epic like one of the bands. They are summarised as a single line: listing the
 * individual artifacts would give away the pool's contents without adding odds.
 */
export function groupEquipmentByChance(items: ShopItem[]): EquipmentGroup[] {
  const groups = new Map<string, ShopItem[]>();
  for (const item of items) {
    // chance is a float; quantize to 1e-9 so rounding noise cannot split a tier.
    const weight = Math.round(item.chance * 1e9);
    const key = `${item.pool ?? 'tier'}:${weight}`;
    const bucket = groups.get(key);
    if (bucket) bucket.push(item);
    else groups.set(key, [item]);
  }
  return [...groups.values()]
    .map((groupItems) => {
      const pool = groupItems[0].pool ?? 'tier';
      return {
        pool,
        rarity: groupItems[0].rarity ?? '',
        rarity_key: groupItems[0].rarity_key ?? '',
        rarity_label: groupItems[0].rarity_label ?? groupItems[0].rarity ?? '',
        // Every entry of a band has the same weight, so one of them is the
        // per-item chance.
        chance: groupItems[0].chance,
        cumulative: groupItems.reduce((sum, item) => sum + item.chance, 0),
        price: uniform(groupItems, (item) => item.price, 0),
        currency: groupItems[0].currency ?? '',
        categories:
          pool === 'mini_artifact' ? [] : groupEquipmentByCategory(groupItems),
        items: groupItems,
      };
    })
    .sort((a, b) => a.cumulative - b.cumulative);
}

/** Second level: split one weight band into 饰品 / 护甲 / 武器. */
function groupEquipmentByCategory(items: ShopItem[]): EquipmentCategoryGroup[] {
  const groups = new Map<string, ShopItem[]>();
  for (const item of items) {
    const key = item.item_category_key ?? '';
    const bucket = groups.get(key);
    if (bucket) bucket.push(item);
    else groups.set(key, [item]);
  }
  return [...groups.entries()]
    .map(([category_key, categoryItems]) => ({
      category_key,
      label: categoryItems[0].item_category_label ?? '',
      cumulative: categoryItems.reduce((sum, item) => sum + item.chance, 0),
      price: uniform(categoryItems, (item) => item.price, 0),
      currency: categoryItems[0].currency ?? '',
      items: categoryItems,
    }))
    .sort((a, b) => a.cumulative - b.cumulative);
}

/** chance (0-1) -> percentage string, e.g. 0.002869 -> "0.2869%" */
export function formatChancePercent(chance: number): string {
  return `${+(chance * 100).toFixed(4)}%`;
}
