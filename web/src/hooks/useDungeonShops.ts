import { useEffect, useState } from 'react';
import type { ShopDetail, ShopIndex } from '../types/data';
import { dataUrl } from '../utils/dataUrl';
import { useDataVersion } from './useDataVersion';

// Per-version caches so navigating between regions does not refetch.
let cachedVersion = '';
const indexCache = new Map<string, Promise<ShopIndex>>();
const detailCache = new Map<string, Promise<ShopDetail>>();

function fetchIndex(version: string): Promise<ShopIndex> {
  if (cachedVersion !== version) {
    indexCache.clear();
    detailCache.clear();
    cachedVersion = version;
  }
  const cached = indexCache.get(version);
  if (cached) return cached;
  const promise = fetch(dataUrl(version, '/data/json/dungeon_shops.json')).then(
    (r) => r.json() as Promise<ShopIndex>
  );
  indexCache.set(version, promise);
  return promise;
}

function fetchDetail(version: string, region: string): Promise<ShopDetail> {
  if (cachedVersion !== version) {
    indexCache.clear();
    detailCache.clear();
    cachedVersion = version;
  }
  const key = `${version}:${region}`;
  const cached = detailCache.get(key);
  if (cached) return cached;
  const promise = fetch(
    dataUrl(version, `/data/json/dungeon_shops/${region}.json`)
  ).then((r) => r.json() as Promise<ShopDetail>);
  detailCache.set(key, promise);
  return promise;
}

/** Shop index (every region) for the list page. */
export function useShopIndex(ssrIndex?: ShopIndex | null) {
  const version = useDataVersion();
  const [index, setIndex] = useState<ShopIndex | null>(ssrIndex ?? null);
  const [loading, setLoading] = useState(!ssrIndex);

  useEffect(() => {
    if (ssrIndex) return;
    if (!version) return;
    let active = true;
    fetchIndex(version)
      .then((data) => {
        if (active) {
          setIndex(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [version, ssrIndex]);

  return { index, loading };
}

/** One region's full stock for the detail page. */
export function useShopDetail(region: string, ssrDetail?: ShopDetail | null) {
  const version = useDataVersion();
  const [detail, setDetail] = useState<ShopDetail | null>(ssrDetail ?? null);
  const [loading, setLoading] = useState(!ssrDetail);

  useEffect(() => {
    if (ssrDetail) return;
    if (!version || !region) return;
    let active = true;
    fetchDetail(version, region)
      .then((data) => {
        if (active) {
          setDetail(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [version, region, ssrDetail]);

  return { detail, loading };
}
