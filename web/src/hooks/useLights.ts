import { useEffect, useState } from 'react';
import type { LightsPayload } from '../types/data';
import { dataUrl } from '../utils/dataUrl';
import { useDataVersion } from './useDataVersion';

// Per-version cache so remounting the page does not refetch.
let cachedVersion = '';
let cache = new Map<string, Promise<LightsPayload>>();

function fetchLights(version: string): Promise<LightsPayload> {
  if (cachedVersion !== version) {
    cache = new Map();
    cachedVersion = version;
  }
  const cached = cache.get(version);
  if (cached) return cached;
  const promise = fetch(dataUrl(version, '/data/json/lights.json')).then(
    (r) => r.json() as Promise<LightsPayload>
  );
  cache.set(version, promise);
  return promise;
}

/** Light-source items for the 【灯】 page. */
export function useLights(ssrData?: LightsPayload | null) {
  const version = useDataVersion();
  const [data, setData] = useState<LightsPayload | null>(ssrData ?? null);
  const [loading, setLoading] = useState(!ssrData);

  useEffect(() => {
    if (ssrData) return;
    if (!version) return;
    let active = true;
    fetchLights(version)
      .then((payload) => {
        if (active) {
          setData(payload);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [version, ssrData]);

  return { data, loading };
}
