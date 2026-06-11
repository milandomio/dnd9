export interface QuestContent {
  type: string;
  target: string;
  count: number;
  loot_state?: string;
  rarity?: string;
}

export interface QuestReward {
  type: string;
  name: string;
  type_key: string;
  count: number;
}

export interface NPCQuest {
  id: string;
  title: string;
  quest_number: number;
  contents: QuestContent[];
  rewards: QuestReward[];
  required: string;
}

export interface NPCEntry {
  npc_name: string;
  npc_name_display: string;
  quest_count: number;
  category: string;
  quests: NPCQuest[];
}
