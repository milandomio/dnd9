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
  sub_pool_names?: string[];
}

export interface GroupDropInfo {
  translation: string;
  translation_key?: string;
  label_prefix?: 'undersea';
  label_type?: 'direct' | 'special' | 'random' | 'other';
  may_be_locked?: boolean;
  spawn_rate: number;
  spawn_rates?: Record<string, number>;
  drop_rates: Record<string, number>;
}

export interface ItemEntity {
  name: string;
  translation: string;
  translation_key?: string;
  category: string;
  monsters: string[];
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
}

export interface MonsterEntity {
  name: string;
  translation: string;
  translation_key?: string;
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
}

export interface PropsEntity {
  name: string;
  translation: string;
  translation_key?: string;
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
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
