import { useEffect, useState } from 'react';

const STORAGE_KEY = 'df5_data_version';
let cachedDate = '';
let cachedSeason = 0;
const listeners = new Set<(v: string) => void>();
const seasonListeners = new Set<(v: number) => void>();
let loadingPromise: Promise<void> | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;

function notify() {
  for (const fn of listeners) fn(cachedDate);
}

function notifySeason() {
  for (const fn of seasonListeners) fn(cachedSeason);
}

function loadDataVersion() {
  if (cachedDate || loadingPromise || typeof window === 'undefined') return;

  loadingPromise = fetch('/data/json/meta.json')
    .then((r) => {
      if (!r.ok) throw new Error(`meta.json request failed: ${r.status}`);
      return r.json();
    })
    .then((d: { dataDate?: string; seasonVersion?: number }) => {
      const remote = d.dataDate || '';
      cachedSeason = d.seasonVersion ?? 0;
      notifySeason();
      if (!remote) throw new Error('meta.json has no dataDate');

      cachedDate = remote;
      notify();
      localStorage.setItem(STORAGE_KEY, remote);
    })
    .catch(() => {
      // Keep retrying instead of allowing consumers to fall back to stale paths.
      retryTimer ??= setTimeout(() => {
        retryTimer = null;
        loadDataVersion();
      }, 5000);
    })
    .finally(() => {
      loadingPromise = null;
    });
}

/** Mounted by NavBar so every routed page shares one version bootstrap. */
export function DataVersionLoader() {
  useEffect(() => {
    loadDataVersion();
  }, []);
  return null;
}

/**
 * Returns the current data version (dataDate from meta.json).
 * Shared across all consumers via module-level subscription.
 */
export function useDataVersion(): string {
  const [date, setDate] = useState(cachedDate);

  useEffect(() => {
    listeners.add(setDate);
    if (cachedDate) setDate(cachedDate);
    loadDataVersion();
    return () => {
      listeners.delete(setDate);
    };
  }, []);

  return date;
}

/**
 * Returns the current season version from meta.json.
 * Used for localStorage cleanup — only clears quest_npc_* keys on season change.
 */
export function useSeasonVersion(): number {
  const [season, setSeason] = useState(cachedSeason);

  useEffect(() => {
    seasonListeners.add(setSeason);
    if (cachedSeason) setSeason(cachedSeason);
    return () => {
      seasonListeners.delete(setSeason);
    };
  }, []);

  return season;
}
