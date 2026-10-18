import { useEffect, useState } from 'react';
import type { LightsPayload } from '../types/data';
import { dataUrl } from '../utils/dataUrl';
import { useDataVersion } from './useDataVersion';

// Per-version cache so remounting the page does not refetch.
let cachedVersion = '';
let cache = new Map<string, Promise<LightsPayload>>();

/** Retry delay after a failed fetch, so a flaky network recovers on its own. */
const RETRY_DELAY_MS = 5000;

function fetchLights(version: string): Promise<LightsPayload> {
  if (cachedVersion !== version) {
    cache = new Map();
    cachedVersion = version;
  }
  const cached = cache.get(version);
  if (cached) return cached;
  const promise = fetch(dataUrl(version, '/data/json/lights.json'))
    .then((r) => {
      if (!r.ok) throw new Error(`lights.json request failed: ${r.status}`);
      return r.json() as Promise<LightsPayload>;
    })
    .catch((error) => {
      // Never cache a rejected promise: a transient failure must be retryable
      // instead of pinning the page to an empty result for the whole version.
      cache.delete(version);
      throw error;
    });
  cache.set(version, promise);
  return promise;
}

/**
 * Light-source items for the 【灯】 page.
 *
 * The page keeps its loading state until the payload actually arrives, so a slow
 * or failing request can never be mistaken for real data (a "0 种灯具" page).
 * Failed fetches retry on their own; `error` exposes the last failure.
 */
export function useLights(ssrData?: LightsPayload | null) {
  const version = useDataVersion();
  const [data, setData] = useState<LightsPayload | null>(ssrData ?? null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (ssrData) return;
    if (!version) return;
    let active = true;
    fetchLights(version)
      .then((payload) => {
        if (active) {
          setError(false);
          setData(payload);
        }
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [version, ssrData, attempt]);

  // Retry until the payload lands; the page stays in its loading state meanwhile.
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setAttempt((n) => n + 1), RETRY_DELAY_MS);
    return () => clearTimeout(timer);
  }, [error, attempt]);

  return { data, loading: !data, error };
}
