export interface IndexEntry {
  page: string;
  label: string;
  count: number;
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
  variant_names?: string[];
}

export interface GroupDropInfo {
  translation: string;
  spawn_rate: number;
  drop_rates: Record<string, number>;
}

export interface ItemEntity {
  name: string;
  translation: string;
  category: string;
  monsters: string[];
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
}

export interface MonsterEntity {
  name: string;
  translation: string;
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
}

export interface PropsEntity {
  name: string;
  translation: string;
  coords: Coord[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
}

export interface DungeonModule {
  name: string;
  names: string[];
  translation: string;
  group: string;
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
