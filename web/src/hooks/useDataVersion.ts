import { useEffect, useState } from 'react';

const STORAGE_KEY = 'df5_data_version';
let cachedDate = '';
let fetchStarted = false;

/**
 * Returns the current data version (dataDate from meta.json).
 * On first client-side mount, fetches meta.json and compares with localStorage.
 * If the version has changed, updates localStorage and reloads the page.
 */
export function useDataVersion(): string {
  const [date, setDate] = useState(cachedDate);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (cachedDate) return;
    if (fetchStarted) return;
    fetchStarted = true;

    fetch('/data/json/meta.json')
      .then((r) => r.json())
      .then((d: { dataDate?: string }) => {
        const remote = d.dataDate || '';
        if (!remote) return;

        cachedDate = remote;
        setDate(remote);

        const local = localStorage.getItem(STORAGE_KEY);
        if (local === null) {
          // First visit — just store, no reload
          localStorage.setItem(STORAGE_KEY, remote);
        } else if (local !== remote) {
          // Version changed — update and reload
          localStorage.setItem(STORAGE_KEY, remote);
          location.reload();
        }
      })
      .catch(() => {});
  }, []);

  return date;
}
