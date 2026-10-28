import type { DungeonModule } from '../types/data';

/**
 * 稀有模块的出现概率（百分比），由后端 `module_spawn_rate.py` 按地图组计算后
 * 写入 `dungeon_modules.json` 的 `spawn_rate` 字段。
 *
 * 当前取值自 `DCDungeonDataAsset.Properties.RareChance`（Crypt = 15），
 * 因此不能在前端硬编码——游戏数值一变，概率就要跟着变。
 */
export function getRareModuleSpawnRate(
  module: Pick<DungeonModule, 'spawn_rate'> | undefined
): number {
  return module?.spawn_rate ?? 0;
}

export function applyModuleSpawnRate(
  rate: number,
  module: Pick<DungeonModule, 'spawn_rate'> | undefined
): number {
  const moduleSpawnRate = getRareModuleSpawnRate(module);
  return moduleSpawnRate > 0 ? (rate * moduleSpawnRate) / 100 : rate;
}
