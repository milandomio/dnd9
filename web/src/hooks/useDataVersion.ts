import { useEffect, useState, useCallback } from 'react';

const STORAGE_KEY = 'df5_data_version';
let cachedDate = '';
let cachedSeason = 0;
let _needsRefresh = false;
const listeners = new Set<(v: string) => void>();
const refreshListeners = new Set<(v: boolean) => void>();
const seasonListeners = new Set<(v: number) => void>();

function notify() {
  for (const fn of listeners) fn(cachedDate);
}

function notifyRefresh() {
  for (const fn of refreshListeners) fn(_needsRefresh);
}

function notifySeason() {
  for (const fn of seasonListeners) fn(cachedSeason);
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

/**
 * Subscribes to the "needs refresh" signal — used by AppInner to show a banner.
 */
export function useRefreshNotice(): {
  needsRefresh: boolean;
  refreshNow: () => void;
} {
  const [needsRefresh, setNeedsRefresh] = useState(_needsRefresh);

  useEffect(() => {
    refreshListeners.add(setNeedsRefresh);
    if (_needsRefresh) setNeedsRefresh(true);
    return () => {
      refreshListeners.delete(setNeedsRefresh);
    };
  }, []);

  const refreshNow = useCallback(() => {
    // Don't clear SW caches — all runtime caching uses StaleWhileRevalidate
    // with stable keys, offline fallback preserved for all resources.
    location.reload();
  }, []);

  return { needsRefresh, refreshNow };
}

// Single fetch — runs once on module load
if (typeof window !== 'undefined') {
  fetch('/data/json/meta.json')
    .then((r) => r.json())
    .then((d: { dataDate?: string; seasonVersion?: number }) => {
      const remote = d.dataDate || '';
      const season = d.seasonVersion ?? 0;

      cachedSeason = season;
      notifySeason();

      if (remote) {
        cachedDate = remote;
        notify();

        const local = localStorage.getItem(STORAGE_KEY);
        if (local === null) {
          localStorage.setItem(STORAGE_KEY, remote);
        } else if (local !== remote) {
          localStorage.setItem(STORAGE_KEY, remote);
          _needsRefresh = true;
          notifyRefresh();
        }
      }
    })
    .catch(() => {});
}
