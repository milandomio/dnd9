import { useState, useEffect } from 'react';
import { useDataVersion } from './useDataVersion';

export interface SearchEntry {
  name: string;
  translation: string;
  page: string;
  url: string;
  tag?: string;
}

let cachedIndex: SearchEntry[] | null = null;
let cachedPromise: Promise<SearchEntry[]> | null = null;
let cachedVersion = '';

function fetchIndex(version: string): Promise<SearchEntry[]> {
  if (cachedIndex && cachedVersion === version)
    return Promise.resolve(cachedIndex);
  if (cachedPromise && cachedVersion === version) return cachedPromise;
  cachedVersion = version;
  cachedPromise = fetch('/data/json/search_index.json')
    .then((r) => r.json())
    .then((data: SearchEntry[]) => {
      cachedIndex = data;
      return data;
    });
  return cachedPromise;
}

/** Get the full search index (for NavBar). */
export function getSearchIndex(version: string): Promise<SearchEntry[]> {
  return fetchIndex(version);
}

/** Get entries filtered by page (for list pages). */
export function getPageEntries(
  version: string,
  page: string
): Promise<SearchEntry[]> {
  return fetchIndex(version).then((idx) => idx.filter((e) => e.page === page));
}

/**
 * React hook that returns the search index state.
 * Triggers a fetch on first mount if not already cached.
 */
export function useSearchIndex() {
  const dataVersion = useDataVersion();
  const [index, setIndex] = useState<SearchEntry[] | null>(() => cachedIndex);
  const [loading, setLoading] = useState(!cachedIndex);

  useEffect(() => {
    if (!dataVersion) return;
    if (cachedIndex && cachedVersion === dataVersion) {
      setIndex(cachedIndex);
      setLoading(false);
      return;
    }
    fetchIndex(dataVersion).then((data) => {
      setIndex(data);
      setLoading(false);
    });
  }, [dataVersion]);

  return { index, loading };
}
