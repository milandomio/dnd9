import { useState, useEffect } from 'react';
import { useDataVersion } from './useDataVersion';
import { type SupportedLang } from '../i18n/locale';
import { dataUrl } from '../utils/dataUrl';

export interface SearchEntry {
  name: string;
  translation: string;
  translation_key?: string;
  page: string;
  url: string;
  tag?: string;
}

const indexCache = new Map<string, SearchEntry[]>();
const pendingIndexes = new Map<string, Promise<SearchEntry[]>>();

function fetchIndex(
  version: string,
  lang: SupportedLang
): Promise<SearchEntry[]> {
  const cacheKey = `${version}:${lang}`;
  const cached = indexCache.get(cacheKey);
  if (cached) return Promise.resolve(cached);
  const pending = pendingIndexes.get(cacheKey);
  if (pending) return pending;
  const promise = fetch(
    dataUrl(version, `/data/json/search_index/${lang}.json`)
  )
    .then((r) => r.json())
    .then((data: SearchEntry[]) => {
      indexCache.set(cacheKey, data);
      pendingIndexes.delete(cacheKey);
      return data;
    });
  pendingIndexes.set(cacheKey, promise);
  return promise;
}

/** Get the full search index (for NavBar). */
export function getSearchIndex(
  version: string,
  lang: SupportedLang
): Promise<SearchEntry[]> {
  return fetchIndex(version, lang);
}

/** Get entries filtered by page (for list pages). */
export function getPageEntries(
  version: string,
  page: string,
  lang: SupportedLang
): Promise<SearchEntry[]> {
  return fetchIndex(version, lang).then((idx) =>
    idx.filter((e) => e.page === page)
  );
}

/**
 * React hook that returns the search index state.
 * Triggers a fetch on first mount if not already cached.
 */
export function useSearchIndex(lang: SupportedLang) {
  const dataVersion = useDataVersion();
  const cacheKey = `${dataVersion}:${lang}`;
  const [index, setIndex] = useState<SearchEntry[] | null>(
    () => indexCache.get(cacheKey) || null
  );
  const [loading, setLoading] = useState(() => !indexCache.has(cacheKey));

  useEffect(() => {
    if (!dataVersion) return;
    const cached = indexCache.get(cacheKey);
    if (cached) {
      setIndex(cached);
      setLoading(false);
      return;
    }
    setIndex(null);
    setLoading(true);
    // 延迟 fetch 到页面首次渲染完成后再发起，避免阻塞关键路径
    const timer = setTimeout(() => {
      fetchIndex(dataVersion, lang)
        .then((data) => {
          setIndex(data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }, 0);
    return () => clearTimeout(timer);
  }, [cacheKey, dataVersion, lang]);

  return { index, loading };
}
