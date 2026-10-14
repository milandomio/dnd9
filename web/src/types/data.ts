export interface IndexEntry {
  page: string;
  label: string;
  count: number;
}

export interface VariantNameEntry {
  translation_key: string;
  name: string;
}

export interface Coord {
  x: number;
  y: number;
  z: number;
  map: string;
  file: string;
  version: string;
  label: string;
  spawn_rate?: number;
  score?: number;
  variant_count?: number;
  variant_names?: VariantNameEntry[];
  group_parent?: string;
  sub_group_parent?: string;
  sub_pool_size?: number;
  sub_pool_entries?: VariantNameEntry[];
  parent_pool_size?: number;
}

export interface LootdropCoord extends Omit<Coord, 'label'> {
  yaw?: number;
  label?: string;
  quality?: string;
}

export interface GroupDropInfo {
  source_id?: string;
  translation: string;
  translation_key?: string;
  label_prefix?: 'undersea';
  label_type?: 'direct' | 'special' | 'random' | 'other';
  may_be_locked?: boolean;
  spawn_rate: number;
  spawn_rates?: Record<string, number>;
  drop_rates: Record<string, number>;
}

export interface LootdropVariantGroupDropInfo {
  source_id: string;
  spawn_rate: number;
  spawn_rates?: Record<string, number>;
  drop_rates: Record<string, number>;
}

export interface LootdropSource {
  name: string;
  entity_name: string;
  translation: string;
  translation_key?: string;
  color: string;
  ref: string;
}

export interface LootdropVariantData {
  group_drop_info: Record<string, LootdropVariantGroupDropInfo[]>;
}

export interface LootdropMonster extends Omit<LootdropSource, 'ref'> {
  source_id?: string;
  ref?: string;
  coords?: LootdropCoord[];
  coord_count?: number;
  drop_rates?: Record<string, number>;
  max_score?: number;
}

export interface LootdropItem {
  name: string;
  translation: string;
  translation_key?: string;
  monsters?: LootdropMonster[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
  sources?: Record<string, LootdropSource>;
  variants?: Record<string, LootdropVariantData>;
  variant_suffixes?: string[];
  variant_rarity?: Record<string, { name: string; translation_key: string }>;
  unavailableVariantSuffix?: string;
}

export interface ItemEntity {
  name: string;
  translation: string;
  translation_key?: string;
  category: string;
  monsters: string[];
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
  isDetailTemplate?: boolean;
}

export interface MonsterLootItem {
  name: string;
  page: string;
  translation: string;
  translation_key?: string;
  suffix: string | null;
  luck_grade: number;
}

export interface MonsterLootPool {
  id: string;
  kind: 'quest' | 'artifact' | 'consumable' | 'misc' | 'pool';
  lootdrop_id: string | null;
  translation?: string;
  translation_key?: string;
  /** Sub-pool suffix locale key (`df5.lootpool.Spoils` etc.) appended to `translation`. */
  sub_label?: string;
  items: MonsterLootItem[];
}

export interface MonsterEntity {
  name: string;
  translation: string;
  translation_key?: string;
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
  loot_pools?: MonsterLootPool[];
  /** Max instances allowed per run (0/undefined = unlimited). */
  session_spawn_limit?: number;
  isDetailTemplate?: boolean;
}

export interface PropsEntity {
  name: string;
  translation: string;
  translation_key?: string;
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
  loot_pools?: MonsterLootPool[];
  isDetailTemplate?: boolean;
}

export interface DungeonModule {
  name: string;
  names: string[];
  translation: string;
  translation_key?: string;
  group: string;
  group_key?: string;
  group_floor?: number;
  group_sub_key?: string;
  group_display?: string;
  size_x: number;
  size_y: number;
  sl_base_name: string;
  all_sl_base_names?: string[];
  img_name: string;
  has_img: boolean;
  has_useful_entities: boolean;
  offset_x: number;
  offset_y: number;
  rotate: number;
  range: number;
}

/** One weighted outcome of a consumable's randomized effect. */
export interface ShopItemEffectRoll {
  effect: string;
  rate: number;
  chance: number;
  /** Numeric effect values keyed by field name (e.g. `Luck`). */
  [field: string]: number | string;
}

export interface ShopItemEffect {
  /** `{field: [min, max]}` across all rolls. */
  values: Record<string, [number, number]>;
  rolls: ShopItemEffectRoll[];
}

export interface ShopItem {
  name: string;
  page: string;
  translation: string;
  translation_key?: string;
  price: number;
  currency: string;
  count: number;
  stock: number;
  rate: number;
  /** Sum of the rates in this item's pool (the slot rolls once). */
  slot_total: number;
  /** Drop chance 0-1; already folded over duplicate slots (8/9). */
  chance: number;
  /** Poor | Common | Uncommon | Rare | Epic | Legend | Unique | Artifact. */
  rarity?: string;
  /** Sold by this region only (not present in any other region's stock). */
  map_exclusive?: boolean;
  /** Resolved gameplay effect (only consumables that roll an effect have it). */
  effect?: ShopItemEffect | null;
}

export interface ShopSlot {
  slot: number;
  items: ShopItem[];
  /** Sum of item chances; ~1 for a single roll, ~2 for the doubled slot. */
  chance_total?: number;
}

export interface ShopDifficulty {
  difficulty: string;
  variant_id: string;
  /** Card count including quality tiers; matches what the page renders. */
  item_count: number;
  /** Distinct items after folding quality suffixes. */
  base_item_count?: number;
  exclusive_count?: number;
  slots: ShopSlot[];
}

export interface ShopRegionSummary {
  region: string;
  label_key?: string;
  display: string;
  /** Card count across difficulties; matches the detail page header. */
  item_count: number;
  /** Distinct items after folding quality suffixes. */
  base_item_count?: number;
  exclusive_count: number;
}

export interface ShopMerchant {
  merchant_name: string;
  translation_key: string;
  greeting_key: string;
  npc_id: string;
  /** Default-language label, embedded because zh-Hans does not load the locale dict. */
  display?: string;
  /** Default-language greeting text. */
  greeting?: string;
}

export interface ShopIndex {
  merchants: ShopMerchant[];
  regions: ShopRegionSummary[];
}

export interface ShopDetail {
  region: string;
  label_key?: string;
  display: string;
  merchant: ShopMerchant;
  exclusive_count: number;
  /** Card count across difficulties; matches the list page. */
  total_items: number;
  /** Distinct items after folding quality suffixes. */
  base_item_count?: number;
  difficulties: ShopDifficulty[];
}
