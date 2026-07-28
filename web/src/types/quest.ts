export interface QuestContent {
  type: string;
  target: string;
  translation_key?: string;
  count: number;
  loot_state?: string;
  rarity?: string;
  rarity_translation_key?: string;
  dungeon_type?: string;
  dungeon_translation_key?: string;
}

export interface QuestReward {
  type: string;
  name: string;
  type_key: string;
  translation_key: string;
  count: number;
}

export interface NPCQuest {
  id: string;
  title: string;
  translation_key: string;
  quest_number: number;
  contents: QuestContent[];
  rewards: QuestReward[];
  required: string;
}

export interface NPCEntry {
  npc_name: string;
  npc_name_display: string;
  translation_key: string;
  quest_count: number;
  category: string;
  quests: NPCQuest[];
}
