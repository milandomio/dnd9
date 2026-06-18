import { useEffect, useState } from 'react';

const STORAGE_KEY = 'df5_data_version';
let cachedDate = '';
let fetchStarted = false;
const listeners = new Set<(v: string) => void>();

function notify() {
  for (const fn of listeners) fn(cachedDate);
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

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (fetchStarted) return;
    fetchStarted = true;

    fetch('/data/json/meta.json')
      .then((r) => r.json())
      .then((d: { dataDate?: string }) => {
        const remote = d.dataDate || '';
        if (!remote) return;

        cachedDate = remote;
        notify();

        const local = localStorage.getItem(STORAGE_KEY);
        if (local === null) {
          localStorage.setItem(STORAGE_KEY, remote);
        } else if (local !== remote) {
          localStorage.setItem(STORAGE_KEY, remote);
          location.reload();
        }
      })
      .catch(() => {});
  }, []);

  return date;
}
