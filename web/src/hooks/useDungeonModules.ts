import { useState, useEffect } from 'react';
import type { DungeonModule } from '../types/data';
import { useDataVersion } from './useDataVersion';
import { dataUrl } from '../utils/dataUrl';

let cachedVersion: string | null = null;
let cachedModules: Map<string, DungeonModule> | null = null;
let cachedPromise: Promise<Map<string, DungeonModule>> | null = null;

function fetchModules(version: string): Promise<Map<string, DungeonModule>> {
  // 版本变化时清除旧缓存
  if (cachedVersion !== version) {
    cachedModules = null;
    cachedPromise = null;
  }
  if (cachedModules) return Promise.resolve(cachedModules);
  if (cachedPromise) return cachedPromise;

  cachedVersion = version;
  cachedPromise = fetch(dataUrl('/data/json/dungeon_modules.json'))
    .then<DungeonModule[]>((r) => r.json())
    .then((mods) => {
      const mm = new Map<string, DungeonModule>();
      mods.forEach((m) => {
        // 注册所有名称（合并后的模块有多个名称）
        const names = m.names || [m.name];
        names.forEach((n) => mm.set(n, m));
        // 注册 sl_base_name
        mm.set(m.sl_base_name, m);
        // 注册所有 sl_base_names（合并后的模块）
        if (m.all_sl_base_names) {
          m.all_sl_base_names.forEach((sl) => mm.set(sl, m));
        }
      });
      cachedModules = mm;
      return mm;
    });

  return cachedPromise;
}

export function useDungeonModules() {
  const dataVersion = useDataVersion();
  const [modules, setModules] = useState<Map<string, DungeonModule>>(
    () => cachedModules ?? new Map()
  );
  const [loading, setLoading] = useState(!cachedModules);

  useEffect(() => {
    if (cachedModules && cachedVersion === dataVersion) {
      setModules(cachedModules);
      setLoading(false);
      return;
    }
    fetchModules(dataVersion).then((mm) => {
      setModules(mm);
      setLoading(false);
    });
  }, [dataVersion]);

  return { modules, loading };
}
