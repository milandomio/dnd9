const RARE_MODULE_SPAWN_RATES: Record<string, number> = {
  Crypt_BlindfallPit: 1,
  Crypt_LightlessChamber_01: 1,
  Crypt_LightlessTomb_01: 1,
  Crypt_MadCorridors: 1,
  Crypt_TorchboundVault: 1,
};

export function getRareModuleSpawnRate(moduleName?: string): number {
  return moduleName ? (RARE_MODULE_SPAWN_RATES[moduleName] ?? 0) : 0;
}
