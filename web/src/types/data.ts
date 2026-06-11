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
}

export interface ItemEntity {
  name: string;
  translation: string;
  category: string;
  monsters: string[];
  coords: Coord[];
}

export interface MonsterEntity {
  name: string;
  translation: string;
  coords: Coord[];
}

export interface PropsEntity {
  name: string;
  translation: string;
  coords: Coord[];
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
