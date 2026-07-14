import { useEffect, useState } from 'react';
import { setDataVersion } from '../utils/dataUrl';

const STORAGE_KEY = 'df5_data_version';
let cachedDate = '';
let cachedSeason = 0;
const listeners = new Set<(v: string) => void>();
const seasonListeners = new Set<(v: number) => void>();

function notify() {
  for (const fn of listeners) fn(cachedDate);
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

// Single fetch — runs once on module load, served by SW (StaleWhileRevalidate, 5min TTL)
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
        setDataVersion(remote);
        notify();
        localStorage.setItem(STORAGE_KEY, remote);
      }
    })
    .catch(() => {});
}
