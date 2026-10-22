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
  /** 同坐标候选池：该点只生成其中之一 */
  point_pool_size?: number;
  point_pool_entries?: VariantNameEntry[];
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

/** One quality variant of a light source with its burn time and light radius. */
export interface LightItem {
  name: string;
  translation: string;
  translation_key?: string;
  raw_name: string;
  /** Poor | Common | Uncommon | Rare | Epic | Legend | Unique | Artifact. */
  rarity: string;
  fuel_seconds: number;
  light_area_radius: number;
}

export interface LightsPayload {
  /** Distinct light-source items (variants folded). */
  count: number;
  items: LightItem[];
  /** Distinct light-emitting props (braziers, lamps, ...) on the 环境 tab. */
  environment_count?: number;
  environment?: EnvironmentLight[];
}

export interface EnvironmentLight {
  name: string;
  translation: string;
  translation_key?: string;
  raw_name: string;
  fuel_seconds: number;
  fuel_seconds_max: number;
  /** True when the prop only burns inside a swarm event. */
  only_in_swarm: boolean;
}

/** One material a crafting recipe consumes. */
export interface CraftRequirement {
  name: string;
  raw_name: string;
  translation: string;
  translation_key?: string;
  rarity: string;
  amount: number;
}

/** A group title fragment: a material name (or the item name for split tiers). */
export type CraftGroupPart = Pick<
  CraftRequirement,
  'name' | 'translation' | 'translation_key'
>;

/** How a section heading is built. */
export type CraftGroupKind =
  /** The synthetic ore tab: one 【矿类】 section. */
  | 'ores'
  /** The item names the section (tiers of one item stay together). */
  | 'item'
  /** The materials that identify the family (「银粉」…). */
  | 'material'
  /** Item category + subtype, the same taxonomy the lootdrops page uses. */
  | 'category';

/** One crafting recipe: a quality tier of an item plus its materials. */
export interface CraftRecipe {
  merchant: string;
  recipe_id: string;
  unique_id: number;
  name: string;
  raw_name: string;
  translation: string;
  translation_key?: string;
  rarity: string;
  requirements: CraftRequirement[];
  /**
   * Section key; recipes of one section sit next to each other. Recipes of the
   * synthetic ore tab all share the `__ores__` key.
   */
  group: string;
  group_kind: CraftGroupKind;
  /** Item category of a `category` section (e.g. 护甲), rendered as its prefix. */
  group_category?: CraftGroupPart;
  /**
   * Heading fragments: materials, the item name, or item subtypes. Joined with
   * ' + ' (or the language delimiter for category sections). Empty for the ore tab.
   */
  group_parts: CraftGroupPart[];
  /** Stat lines of the crafted item; absent for materials and old payloads. */
  properties?: CraftProperties;
  /**
   * Consumable effect of the crafted item (a Protection potion's shield amount
   * and duration). Absent for equipment and items without an effect summary.
   */
  effect?: CraftEffect;
}

/** One stat line of a crafted item (armour rating, weapon damage, …). */
export interface CraftProperty {
  /** Property type without its asset prefix (``Effect_ArmorRating``). */
  type: string;
  translation: string;
  translation_key?: string;
  /** Lowest value the item rolls. */
  min: number;
  /** Highest value the item rolls (equal to ``min`` for fixed stats). */
  max: number;
  /**
   * ``ValueRatio`` of the property type. 0.001 marks the percentage stats, so
   * a raw 20 renders as ``2%`` exactly like the in-game tooltip; without it the
   * value is a flat number (armour rating 19, move speed -30).
   */
  ratio?: number;
  /** Draw chance inside a random pool (pool entries only). */
  chance?: number;
}

/** Stat lines shown under the materials of a crafted item. */
export interface CraftProperties {
  /** Fixed stats of the item. */
  primary: CraftProperty[];
  /**
   * The extra enchantment slots: ``rolls`` random stats drawn from the pool
   * shared by every item of the same equipment slot (``property_pools``).
   */
  random?: { rolls: number; pool: string };
}

/**
 * One consumable effect line (幸运 / 最大物理护盾 / 持续时间 …).
 *
 * Unlike a stat line it carries no ``ratio``: the value is what the game shows
 * in the tooltip, already converted from the asset (a millisecond duration
 * becomes seconds, a raw shield amount stays flat).
 */
export interface CraftEffectProperty {
  /** Effect field without its asset prefix (``MaxPhysicalShield``). */
  type: string;
  translation: string;
  translation_key?: string;
  /** Lowest value the item grants (equal to ``max`` for a fixed effect). */
  min: number;
  /** Highest value the item grants. */
  max: number;
  /** True when the value is a duration in seconds (renders as 「24 秒」). */
  seconds?: boolean;
}

/** Effect of a crafted consumable (a Protection potion's shield and duration). */
export interface CraftEffect {
  /** Every effect line the item grants. */
  values: CraftEffectProperty[];
  /**
   * True when the effect is rolled at random (Luck potions); a fixed shield
   * (Protection potions) always grants the same numbers.
   */
  random?: boolean;
}

/** A crafting NPC tab (or the synthetic 【矿类】 tab). */
export interface CraftMerchant {
  name: string;
  /** URL slug of the tab route (``/crafts/{slug}/``): ``alchemist``, ``ores``. */
  slug: string;
  /** 'npc' for a real merchant, 'ores' for the synthetic ore-refining tab. */
  kind: string;
  translation_key?: string;
  /** zh-Hans fallback for the default language. */
  display: string;
  group_count: number;
  item_count: number;
  recipe_count: number;
}

export interface CraftsPayload {
  /** Distinct crafting tabs. */
  count: number;
  /** Distinct (merchant, section) pairs the page renders. */
  group_count: number;
  /** Distinct (merchant, item) pairs. */
  item_count: number;
  /** Total recipes. */
  recipe_count: number;
  /** Merchant name of the synthetic ore-refining tab. */
  ores_merchant?: string;
  /**
   * Random stat pools by asset name (``Id_ItemProperty_Secondary_Chest``).
   * Shared by every recipe of one equipment slot, so recipes only reference
   * them instead of repeating the pool.
   */
  property_pools?: Record<string, CraftProperty[]>;
  merchants: CraftMerchant[];
  recipes: CraftRecipe[];
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
