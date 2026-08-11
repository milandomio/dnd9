import { useState, useEffect } from 'react';
import type { DungeonModule } from '../types/data';
import { useDataVersion } from './useDataVersion';

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
  const verShort = Number(version).toString(36);
  cachedPromise = fetch(`/data/${verShort}/json/dungeon_modules.json`)
    .then<DungeonModule[]>((r) => r.json())
    .then((mods) => {
      const mm = new Map<string, DungeonModule>();
      mods.forEach((m) => {
        // 注册所有名称（合并后的模块有多个名称）
        const names = m.names || [m.name];
        names.forEach((n) => mm.set(n, m));
        // 注册 sl_base_name
        mm.set(m.sl_base_name, m);
        // Quest explore targets carry the module translation key rather than the canonical name.
        if (m.translation_key) mm.set(m.translation_key, m);
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

export function useDungeonModules(options?: { defer?: boolean }) {
  const dataVersion = useDataVersion();
  const defer = options?.defer ?? false;
  const [modules, setModules] = useState<Map<string, DungeonModule>>(
    () => cachedModules ?? new Map()
  );
  const [loading, setLoading] = useState(!cachedModules);

  useEffect(() => {
    if (!dataVersion) return;
    if (cachedModules && cachedVersion === dataVersion) {
      setModules(cachedModules);
      setLoading(false);
      return;
    }

    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let frame: number | undefined;
    const load = () => {
      fetchModules(dataVersion)
        .then((mm) => {
          if (!active) return;
          setModules(mm);
          setLoading(false);
        })
        .catch(() => {
          if (active) setLoading(false);
        });
    };

    if (defer) {
      // Let the current page paint before the global cache warm-up starts.
      frame = window.requestAnimationFrame(() => {
        timer = setTimeout(load, 0);
      });
    } else {
      load();
    }

    return () => {
      active = false;
      if (frame !== undefined) window.cancelAnimationFrame(frame);
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [dataVersion, defer]);

  return { modules, loading };
}
