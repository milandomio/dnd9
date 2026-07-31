const RARE_MODULE_BASE_SPAWN_RATE = 1;
const CRYPT_GRID_CELL_COUNT = 25;
const CENTER_TOWER_COVERED_CELL_COUNT = 4;
const RARE_MODULE_SPAWN_RATE =
  (RARE_MODULE_BASE_SPAWN_RATE *
    (CRYPT_GRID_CELL_COUNT - CENTER_TOWER_COVERED_CELL_COUNT)) /
  CRYPT_GRID_CELL_COUNT;

const RARE_MODULE_SPAWN_RATES: Record<string, number> = {
  Crypt_BlindfallPit: RARE_MODULE_SPAWN_RATE,
  Crypt_LightlessChamber_01: RARE_MODULE_SPAWN_RATE,
  Crypt_LightlessTomb_01: RARE_MODULE_SPAWN_RATE,
  Crypt_MadCorridors: RARE_MODULE_SPAWN_RATE,
  Crypt_TorchboundVault: RARE_MODULE_SPAWN_RATE,
};

export function getRareModuleSpawnRate(moduleName?: string): number {
  return moduleName ? (RARE_MODULE_SPAWN_RATES[moduleName] ?? 0) : 0;
}

export function applyModuleSpawnRate(
  rate: number,
  moduleName?: string
): number {
  const moduleSpawnRate = getRareModuleSpawnRate(moduleName);
  return moduleSpawnRate > 0 ? (rate * moduleSpawnRate) / 100 : rate;
}
