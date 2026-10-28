export const QUEST_SEASON_KEY = 'quest_npc_season';
const QUEST_PROGRESS_PREFIX = 'quest_npc_';

export function isQuestSeasonCurrent(seasonVersion: number): boolean {
  try {
    return localStorage.getItem(QUEST_SEASON_KEY) === String(seasonVersion);
  } catch {
    return true;
  }
}

/**
 * Drops every saved NPC, quest, and objective mark for the current quest table,
 * then records the season so the automatic migration does not repeat.
 */
export function resetQuestProgress(seasonVersion: number): void {
  const toRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(QUEST_PROGRESS_PREFIX)) toRemove.push(key);
  }
  toRemove.forEach((key) => localStorage.removeItem(key));
  localStorage.setItem(QUEST_SEASON_KEY, String(seasonVersion));
}
