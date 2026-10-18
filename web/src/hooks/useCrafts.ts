import { useEffect, useState } from 'react';
import type { CraftsPayload } from '../types/data';
import { dataUrl } from '../utils/dataUrl';
import { useDataVersion } from './useDataVersion';

// Per-version cache so remounting the page does not refetch.
let cachedVersion = '';
let cache = new Map<string, Promise<CraftsPayload>>();

/** Retry delay after a failed fetch, so a flaky network recovers on its own. */
const RETRY_DELAY_MS = 5000;

function fetchCrafts(version: string): Promise<CraftsPayload> {
  if (cachedVersion !== version) {
    cache = new Map();
    cachedVersion = version;
  }
  const cached = cache.get(version);
  if (cached) return cached;
  const promise = fetch(dataUrl(version, '/data/json/crafts.json'))
    .then((r) => {
      if (!r.ok) throw new Error(`crafts.json request failed: ${r.status}`);
      return r.json() as Promise<CraftsPayload>;
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
 * Crafting recipes for the 【工匠】 page.
 *
 * The page keeps its loading state until the payload actually arrives, so a slow
 * or failing request can never be mistaken for real data (an empty page).
 * Failed fetches retry on their own; `error` exposes the last failure.
 */
export function useCrafts(ssrData?: CraftsPayload | null) {
  const version = useDataVersion();
  const [data, setData] = useState<CraftsPayload | null>(ssrData ?? null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (ssrData) return;
    if (!version) return;
    let active = true;
    fetchCrafts(version)
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
