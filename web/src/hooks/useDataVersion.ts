import { useEffect, useState, useCallback } from 'react';

const STORAGE_KEY = 'df5_data_version';
let cachedDate = '';
let fetchStarted = false;
let _needsRefresh = false;
const listeners = new Set<(v: string) => void>();
const refreshListeners = new Set<(v: boolean) => void>();

function notify() {
  for (const fn of listeners) fn(cachedDate);
}

function notifyRefresh() {
  for (const fn of refreshListeners) fn(_needsRefresh);
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
          _needsRefresh = true;
          notifyRefresh();
        }
      })
      .catch(() => {});
  }, []);

  return date;
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
    location.reload();
  }, []);

  return { needsRefresh, refreshNow };
}
