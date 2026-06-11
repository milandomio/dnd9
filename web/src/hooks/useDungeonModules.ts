import { useState, useEffect } from 'react';
import type { DungeonModule } from '../types/data';

let cachedModules: Map<string, DungeonModule> | null = null;
let cachedPromise: Promise<Map<string, DungeonModule>> | null = null;

function fetchModules(): Promise<Map<string, DungeonModule>> {
  if (cachedModules) return Promise.resolve(cachedModules);
  if (cachedPromise) return cachedPromise;

  cachedPromise = fetch('./data/json/dungeon_modules.json')
    .then<DungeonModule[]>((r) => r.json())
    .then((mods) => {
      const mm = new Map<string, DungeonModule>();
      mods.forEach((m) => {
        mm.set(m.name, m);
        mm.set(m.sl_base_name, m);
      });
      cachedModules = mm;
      return mm;
    });

  return cachedPromise;
}

export function useDungeonModules() {
  const [modules, setModules] = useState<Map<string, DungeonModule>>(
    () => cachedModules ?? new Map()
  );
  const [loading, setLoading] = useState(!cachedModules);

  useEffect(() => {
    if (cachedModules) {
      setModules(cachedModules);
      setLoading(false);
      return;
    }
    fetchModules().then((mm) => {
      setModules(mm);
      setLoading(false);
    });
  }, []);

  return { modules, loading };
}
