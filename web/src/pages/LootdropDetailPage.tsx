import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useDataVersion } from '../hooks/useDataVersion';
import { useDungeonModules } from '../hooks/useDungeonModules';
import { useDebug } from '../hooks/useDebug';
import { useTheme } from '../hooks/useTheme';
import { dataUrl } from '../utils/dataUrl';
import { dropRateModeLabel } from '../utils/dropRate';
import { formatGroupLabel } from '../utils/formatGroupLabel';
import SectionHeader from '../components/SectionHeader';
import VariantSwitch from '../components/VariantSwitch';
import DebugPanel from '../components/DebugPanel';
import { useSSRData } from '../context/SSRDataContext';
import type {
  DungeonModule,
  GroupDropInfo,
  LootdropCoord,
  LootdropItem,
  LootdropMonster,
  VariantNameEntry,
} from '../types/data';
import {
  getAdj,
  useCtrlBtn,
  useCtrlInput,
  type AdjState,
} from '../components/MapDebug';
import Disclaimer from '../components/Disclaimer';
import DebugCoordTable from '../components/DebugCoordTable';
import LocationStats from '../components/LocationStats';
import ReferenceDropRates from '../components/ReferenceDropRates';
import CompositeRate from '../components/CompositeRate';
import MapPanel from '../components/MapPanel';
import MapImageRecognition from '../components/MapImageRecognition';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import {
  applyModuleSpawnRate,
  getRareModuleSpawnRate,
} from '../utils/moduleSpawnRate';
import { defaultVariantSuffix } from '../utils/variant';
import { localizedSeoDescription } from '../i18n/seo';
import { isRecognizableMapImage, mapImageUrl } from '../utils/mapImage';
import type { MapImageTemplate } from '../utils/mapImageRecognition';

// P005: Global ref coord cache — shared across all LootdropDetailPage instances
const _globalRefCache = new Map<string, LootdropCoord[]>();
const _globalRefPending = new Map<string, Promise<LootdropCoord[]>>();
const _globalLootCache = new Map<string, LootdropItem>();
const _globalLootPending = new Map<string, Promise<LootdropItem>>();
let _globalCacheVersion = '';

const GROUP_ORDER = [
  'GoblinCave',
  'FireDeep',
  'IceCavern',
  'IceAbyss',
  'Ruins',
  'Crypt',
  'Inferno',
  'ShipGraveyard',
];

const VARIANT_RE = /^(.+?)_(\d{4})$/;
const LOOT_SOURCE_UI_KEYS: Record<string, string> = {
  Weapon_DualBoss: 'ui.loot_source.dual_boss_weapon',
  Weapon_MysticalTreasureRoom: 'ui.loot_source.mystical_treasure_weapon',
  Weapon: 'ui.loot_source.weapon',
  Weapon_GoldenRoom: 'ui.loot_source.golden_room_weapon',
  DwarfSecretWeapon: 'ui.loot_source.dwarf_secret_weapon',
  Weapon_FrozenRoom: 'ui.loot_source.frozen_room_weapon',
  Weapon_SkullRoom: 'ui.loot_source.skull_room_weapon',
};
const RARITY_COLORS: Record<string, string> = {
  Poor: '#9E9E9E',
  Common: '#BDBDBD',
  Uncommon: '#2ECC71',
  Rare: '#3498DB',
  Epic: '#9B59B6',
  Legend: '#F39C12',
  Unique: '#FFD700',
  Artifact: '#FF4500',
};

function getRarityColor(
  vr: { name: string; translation_key: string } | undefined,
  fallback: string
): string {
  if (!vr) return fallback;
  const rn = vr.translation_key.split('_').pop() || '';
  return RARITY_COLORS[rn] ?? fallback;
}

function hasAnyRate(dr: Record<string, number>): boolean {
  return Object.values(dr).some((v) => v > 0);
}

function lootdropSourceKey(monster: LootdropMonster): string {
  return monster.source_id ?? monster.translation;
}

function lootdropSourceTranslationKey(
  source: Pick<LootdropMonster, 'name' | 'entity_name' | 'translation_key'>
): string | undefined {
  return (
    source.translation_key ||
    LOOT_SOURCE_UI_KEYS[source.entity_name ?? source.name]
  );
}

function matchesGroupEntry(
  entry: GroupDropInfo,
  monster: LootdropMonster
): boolean {
  return entry.source_id
    ? entry.source_id === monster.source_id
    : entry.translation === monster.translation;
}

function hasLootdropDetail(item: LootdropItem | undefined): boolean {
  return Boolean(item?.monsters || item?.sources);
}

function stripTrailingParenthetical(value: string): string {
  return value.replace(/\s*[（(][^（）()]*[）)]\s*$/, '').trim();
}

function selectLootdropVariant(
  item: LootdropItem,
  requestedSuffix: string | null
): LootdropItem {
  if (!item.sources || !item.variants) return item;
  const availableSuffixes = Object.keys(item.variants);
  if (requestedSuffix && !item.variants[requestedSuffix]) {
    return {
      ...item,
      name: `${item.name}_${requestedSuffix}`,
      monsters: [],
      group_drop_info: {},
      unavailableVariantSuffix: requestedSuffix,
    };
  }
  const suffix =
    requestedSuffix ?? defaultVariantSuffix(availableSuffixes) ?? '';
  const variant = item.variants[suffix];
  if (!variant) return { ...item, monsters: [], group_drop_info: {} };

  const activeSourceIds = new Set<string>();
  const groupDropInfo: Record<string, GroupDropInfo[]> = {};
  for (const [group, entries] of Object.entries(variant.group_drop_info)) {
    groupDropInfo[group] = entries.flatMap((entry) => {
      const source = item.sources?.[entry.source_id];
      if (!source) return [];
      activeSourceIds.add(entry.source_id);
      return [
        {
          ...entry,
          translation: source.translation,
          translation_key: lootdropSourceTranslationKey(source),
        },
      ];
    });
  }

  const maxScores = new Map<string, number>();
  for (const entries of Object.values(groupDropInfo)) {
    for (const entry of entries) {
      const score =
        Math.round(entry.spawn_rate * (entry.drop_rates['豪客赛'] ?? 0) * 100) /
        10000;
      maxScores.set(
        entry.source_id!,
        Math.max(maxScores.get(entry.source_id!) ?? -1, score)
      );
    }
  }
  const monsters = Object.entries(item.sources)
    .filter(([sourceId]) => activeSourceIds.has(sourceId))
    .map(([sourceId, source]) => ({
      ...source,
      source_id: sourceId,
      translation_key: lootdropSourceTranslationKey(source),
      max_score: maxScores.get(sourceId) ?? -1,
    }));
  return {
    ...item,
    name: suffix ? `${item.name}_${suffix}` : item.name,
    monsters,
    group_drop_info: groupDropInfo,
  };
}

function resetGlobalCaches(dataVersion: string) {
  if (!dataVersion || dataVersion === _globalCacheVersion) return;
  _globalRefCache.clear();
  _globalRefPending.clear();
  _globalLootCache.clear();
  _globalLootPending.clear();
  _globalCacheVersion = dataVersion;
}

export default function LootdropDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const decodedName = decodeURIComponent(name ?? '');
  const variantMatch = decodedName.match(VARIANT_RE);
  // _8001 artifacts are independent entries, not variants of a base item
  const isVariant = variantMatch && variantMatch[2] !== '8001';
  const baseName = isVariant ? variantMatch![1] : decodedName;
  const currentSuffix = isVariant
    ? variantMatch![2]
    : variantMatch && variantMatch[2] === '8001'
      ? '8001'
      : null;
  // itemName is always the base item name (without any variant suffix), used for navigation
  const itemName = variantMatch ? variantMatch[1] : decodedName;
  const dataKey = `lootdrops/${decodedName}`;
  const baseDataKey = `lootdrops/${baseName}`;
  const ssrData = useSSRData<{ item: LootdropItem; modules: DungeonModule[] }>(
    dataKey
  );
  const baseSsrData = useSSRData<{
    item: LootdropItem;
    modules: DungeonModule[];
  }>(baseDataKey);
  const effectiveSsrData = hasLootdropDetail(ssrData?.item)
    ? ssrData
    : hasLootdropDetail(baseSsrData?.item)
      ? baseSsrData
      : ssrData?.item?.name
        ? ssrData
        : baseSsrData?.item?.name
          ? baseSsrData
          : null;
  const [data, setData] = useState<LootdropItem | null>(
    hasLootdropDetail(effectiveSsrData?.item)
      ? selectLootdropVariant(effectiveSsrData!.item, currentSuffix)
      : effectiveSsrData?.item?.name
        ? (effectiveSsrData.item as LootdropItem)
        : null
  );
  const dataVersion = useDataVersion();
  const { modules: globalModules } = useDungeonModules();
  // P005: Initialize refCoords from SSR data if available
  const ssrRefCoords = (effectiveSsrData as any)?._refCoords;
  const initialRefCoords = useMemo(() => {
    if (!ssrRefCoords) return new Map();
    const map = new Map<string, LootdropCoord[]>();
    for (const [ref, coords] of Object.entries(ssrRefCoords)) {
      map.set(ref, coords as LootdropCoord[]);
    }
    return map;
  }, [ssrRefCoords]);

  function defaultHidden(
    monsters: LootdropMonster[],
    threshold: number
  ): Set<string> {
    const init = new Set<string>();
    for (const m of monsters) {
      if (m.name.endsWith('_Elite')) continue;
      const sc = m.max_score;
      if (sc == null || sc < 0) continue;
      if (sc < threshold) init.add(m.translation);
    }
    return init;
  }
  const modules = globalModules;
  const isArtifact = baseName.endsWith('_8001');
  const defaultThreshold = isArtifact ? 0.03 : 2.5;
  const [hidden, setHidden] = useState<Set<string>>(() =>
    hasLootdropDetail(effectiveSsrData?.item)
      ? defaultHidden(
          selectLootdropVariant(effectiveSsrData!.item, currentSuffix)
            .monsters ?? [],
          defaultThreshold
        )
      : new Set()
  );
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set()); // per-coord toggle: \"monsterName-index\"
  const [threshold, setThreshold] = useState(defaultThreshold);
  const [modeFilter, setModeFilter] = useState('');
  const [hideZeroRate, setHideZeroRate] = useState(true);
  const [mapRecognitionEnabled, setMapRecognitionEnabled] = useState(false);
  const [qualityFilter, setQualityFilter] = useState('High');
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();
  const { tokens, dark } = useTheme();
  const { t, ut, lang, dict } = useLocale();
  const delimiter = ['zh-Hans', 'zh-Hant', 'ja'].includes(lang) ? '、' : ', ';
  const ctrlBtn = useCtrlBtn();
  const ctrlInput = useCtrlInput();
  useEffect(() => {
    if (!baseName) return;
    if (dataVersion) resetGlobalCaches(dataVersion);
    if (hasLootdropDetail(effectiveSsrData?.item)) {
      const selected = selectLootdropVariant(
        effectiveSsrData!.item,
        currentSuffix
      );
      _globalLootCache.set(baseName, effectiveSsrData!.item);
      setData(selected);
      setHidden(defaultHidden(selected.monsters ?? [], defaultThreshold));
      return;
    }
    if (!dataVersion) return;
    let cancelled = false;
    const cached = _globalLootCache.get(baseName);
    const pending = _globalLootPending.get(baseName);
    const request = cached
      ? Promise.resolve(cached)
      : (pending ??
        fetch(dataUrl(dataVersion, `/data/json/lootdrops/${baseName}.json`))
          .then((response) => {
            if (!response.ok)
              throw new Error(`lootdrop HTTP ${response.status}`);
            return response.json() as Promise<LootdropItem>;
          })
          .then((item) => {
            _globalLootCache.set(baseName, item);
            _globalLootPending.delete(baseName);
            return item;
          }));
    if (!cached && !pending) _globalLootPending.set(baseName, request);
    if (!cached) {
      setData(null);
      setHidden(new Set());
    }
    request
      .then((item) => {
        if (cancelled) return;
        const selected = selectLootdropVariant(item, currentSuffix);
        setData(selected);
        setHidden(defaultHidden(selected.monsters ?? [], defaultThreshold));
      })
      .catch((error) => {
        _globalLootPending.delete(baseName);
        if (!cancelled) console.error(error);
      });
    return () => {
      cancelled = true;
    };
  }, [baseName, currentSuffix, effectiveSsrData, dataVersion]);

  // Base URLs redirect to a real variant; explicit unavailable variants stay at 0%.
  useEffect(() => {
    const suffixes = data?.variants ? Object.keys(data.variants) : [];
    if (suffixes.length <= 1) return;
    if (currentSuffix) return;
    const defaultSuffix = defaultVariantSuffix(suffixes);
    if (!defaultSuffix) return;
    navigate(`/${lang}/lootdrops/${itemName}_${defaultSuffix}/`, {
      replace: true,
    });
  }, [data, currentSuffix, itemName, lang, navigate]);

  // 在调试模式下实时响应阈值变化
  useEffect(() => {
    if (!data?.monsters) return;
    setHidden(defaultHidden(data.monsters, threshold));
  }, [threshold]);

  const [visibleMaps, setVisibleMaps] = useState<Set<string>>(new Set());
  const observerRef = useRef<IntersectionObserver | null>(null);

  const mapRef = useCallback((mapName: string, el: HTMLDivElement | null) => {
    if (!el) return;
    if (!observerRef.current) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          setVisibleMaps((prev) => {
            const next = new Set(prev);
            for (const e of entries) {
              const mn = (e.target as HTMLElement).dataset.mapName!;
              if (e.isIntersecting) {
                next.add(mn);
              } else {
                next.delete(mn);
              }
            }
            return next;
          });
        },
        { rootMargin: '600px' }
      );
    }
    (el as any).dataset.mapName = mapName;
    observerRef.current.observe(el);
  }, []);

  // Reset lazy-load state when name changes (navigation between lootdrops)
  useEffect(() => {
    setVisibleMaps(new Set());
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
  }, [name]);

  const monsters = data?.monsters ?? [];
  // P005: Load referenced entity coordinates (with global cache)
  const [refCoords, setRefCoords] = useState<Map<string, LootdropCoord[]>>(
    () => {
      const map = new Map<string, LootdropCoord[]>();
      for (const [k, v] of _globalRefCache) map.set(k, v);
      for (const [k, v] of initialRefCoords) map.set(k, v);
      return map;
    }
  );
  useEffect(() => {
    if (dataVersion) resetGlobalCaches(dataVersion);
    const refsNeeded = monsters
      .filter((m) => m.ref && !refCoords.has(m.ref))
      .map((m) => m.ref!);
    if (refsNeeded.length === 0) return;

    const fetchRef = (ref: string): Promise<[string, LootdropCoord[]]> => {
      // Return from global cache if available
      if (_globalRefCache.has(ref)) {
        return Promise.resolve([ref, _globalRefCache.get(ref)!]);
      }
      // Deduplicate in-flight requests
      if (_globalRefPending.has(ref)) {
        return _globalRefPending.get(ref)!.then((coords) => [ref, coords]);
      }
      const p = fetch(dataUrl(dataVersion, `/data/json/${ref}.json`))
        .then((r) => r.json())
        .then((entity) => {
          const coords: LootdropCoord[] = Array.isArray(entity)
            ? entity
            : entity.coords || [];
          _globalRefCache.set(ref, coords);
          _globalRefPending.delete(ref);
          return coords;
        });
      _globalRefPending.set(ref, p);
      return p.then((coords) => [ref, coords]);
    };

    Promise.all(refsNeeded.map(fetchRef)).then((results) => {
      setRefCoords((prev) => {
        const next = new Map(prev);
        for (const [ref, coords] of results) next.set(ref, coords);
        return next;
      });
    });
  }, [monsters, dataVersion]);

  const variantRatesBySource = useMemo(() => {
    const lookup = new Map<string, Map<string, GroupDropInfo>>();
    for (const [group, entries] of Object.entries(
      data?.group_drop_info ?? {}
    )) {
      for (const entry of entries) {
        if (!entry.source_id) continue;
        if (!lookup.has(entry.source_id)) {
          lookup.set(entry.source_id, new Map());
        }
        lookup.get(entry.source_id)!.set(group, entry);
      }
    }
    return lookup;
  }, [data?.group_drop_info]);

  // Merged families use source-level group rates as the coordinate authority.
  const resolvedMonsters = useMemo(
    () =>
      monsters.map((m) => {
        const sourceRates = m.source_id
          ? variantRatesBySource.get(m.source_id)
          : undefined;
        const coords = (m.coords ?? refCoords.get(m.ref!) ?? []).flatMap(
          (coord) => {
            if (!m.ref || modules.size === 0) return [coord];
            const group = modules.get(coord.map)?.group;
            if (!group) return [];
            if (!sourceRates) return [coord];
            const rate = sourceRates.get(group);
            if (!rate) return [];
            return [
              {
                ...coord,
                spawn_rate: rate.spawn_rate,
                score:
                  Math.round(
                    rate.spawn_rate * (rate.drop_rates['豪客赛'] ?? 0) * 100
                  ) / 10000,
              },
            ];
          }
        );
        return { ...m, coords };
      }),
    [monsters, refCoords, modules, variantRatesBySource]
  );

  const orderedMonsters = useMemo(() => {
    return [...resolvedMonsters].sort(
      (a, b) => (b.max_score ?? -1) - (a.max_score ?? -1)
    );
  }, [resolvedMonsters]);

  // Build group_drop_info lookup for score-based module sorting
  const groupDropRateLookup = useMemo(() => {
    const lookup = new Map<string, Map<string, { sr: number; dr: number }>>();
    if (!data?.group_drop_info) return lookup;
    for (const [g, entries] of Object.entries(data.group_drop_info)) {
      const m = new Map<string, { sr: number; dr: number }>();
      for (const e of entries) {
        m.set(e.source_id ?? e.translation, {
          sr: e.spawn_rate,
          dr: e.drop_rates['豪客赛'] ?? 0,
        });
        if (!e.source_id) continue;
        m.set(e.translation, {
          sr: e.spawn_rate,
          dr: e.drop_rates['豪客赛'] ?? 0,
        });
      }
      lookup.set(g, m);
    }
    return lookup;
  }, [data?.group_drop_info]);

  // P005: Show loading state while fetching referenced coords
  const hasRefs = monsters.some((m) => m.ref);
  const refsLoaded =
    !hasRefs || monsters.every((m) => !m.ref || refCoords.has(m.ref!));

  if (!data || !refsLoaded)
    return (
      <div style={{ textAlign: 'center', color: '#ff6b6b', marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  function myGetAdj(mapName: string, mod: DungeonModule | undefined) {
    return getAdj(mapName, mod?.rotate, adjOffsets);
  }

  function setAdj(mapName: string, field: string, value: number | boolean) {
    setAdjOffsets((prev: AdjState) => {
      const cur = prev[mapName] || {
        x: 0,
        y: 0,
        range: 0,
        rotate: 0,
        mirrorX: false,
        mirrorY: false,
      };
      return { ...prev, [mapName]: { ...cur, [field]: value } };
    });
  }

  const toggle = (monsterName: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(monsterName)) next.delete(monsterName);
      else next.add(monsterName);
      return next;
    });
  };

  const toggleRow = (key: string, forceShow?: boolean) => {
    setHiddenRows((prev) => {
      const next = new Set(prev);
      const currentlyHidden = next.has(key);
      if (forceShow === true || (forceShow === undefined && currentlyHidden)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };
  // Build per-map coordinate groups
  const mapGroups = new Map<
    string,
    {
      mod?: DungeonModule;
      dots: {
        monster: LootdropMonster;
        x: number;
        y: number;
        z: number;
        file: string;
        idx: number;
        spawn_rate?: number;
        variant_count?: number;
        variant_names?: VariantNameEntry[];
        score?: number;
        group_parent?: string;
        sub_group_parent?: string;
        sub_pool_size?: number;
        sub_pool_entries?: VariantNameEntry[];
        quality?: string;
      }[];
    }
  >();
  for (const m of resolvedMonsters) {
    m.coords.forEach((c, j) => {
      if (hidden.has(m.translation) || hiddenRows.has(`${m.translation}-${j}`))
        return;
      if (qualityFilter && c.quality && c.quality !== qualityFilter) return;
      if (!mapGroups.has(c.map))
        mapGroups.set(c.map, { mod: modules.get(c.map), dots: [] });
      mapGroups.get(c.map)!.dots.push({
        monster: m,
        x: c.x,
        y: c.y,
        z: c.z,
        file: c.file,
        idx: j,
        spawn_rate: c.spawn_rate,
        variant_count: c.variant_count,
        variant_names: c.variant_names,
        score: c.score,
        group_parent: c.group_parent,
        sub_group_parent: c.sub_group_parent,
        sub_pool_size: c.sub_pool_size,
        sub_pool_entries: c.sub_pool_entries,
        quality: c.quality,
      });
    });
  }

  // Group by module group
  const groupedByType = new Map<string, typeof items>();
  const items = [...mapGroups.entries()].map(([mapName, { mod, dots }]) => ({
    mapName,
    mod,
    dots,
  }));
  for (const item of items) {
    const g = item.mod?.group || '';
    if (!groupedByType.has(g)) groupedByType.set(g, []);
    groupedByType.get(g)!.push(item);
  }

  function computeModuleScore(
    item: {
      mapName?: string;
      mod?: DungeonModule;
      dots: {
        monster: LootdropMonster;
        x: number;
        y: number;
        z: number;
        variant_count?: number;
        variant_names?: VariantNameEntry[];
        score?: number;
        file: string;
        group_parent?: string;
        quality?: string;
      }[];
    },
    _rateLookup: Map<string, { sr: number; dr: number }>
  ): number {
    let total = 0;
    const varGroups = new Map<
      string,
      { sourceKey: string; positions: Set<string>; vc: number }
    >();
    const regPositions = new Map<string, number>();
    for (const d of item.dots) {
      const vc = d.variant_count ?? 1;
      const posKey = `${d.x},${d.y},${d.z}`;
      if (vc > 1) {
        const key = d.group_parent || `${d.file}::${vc}`;
        const existing = varGroups.get(key);
        if (existing) {
          existing.positions.add(posKey);
        } else {
          varGroups.set(key, {
            sourceKey: lootdropSourceKey(d.monster),
            positions: new Set([posKey]),
            vc,
          });
        }
      } else {
        const mKey = `${d.monster.translation}::${posKey}`;
        let s = d.score ?? 0;
        if (s === 0) {
          const rate = _rateLookup.get(lootdropSourceKey(d.monster));
          if (rate) s = (rate.sr * rate.dr) / 100;
        }
        const prev = regPositions.get(mKey) ?? 0;
        if (s > prev) regPositions.set(mKey, s);
      }
    }
    for (const s of regPositions.values()) total += s;
    for (const [, g] of varGroups) {
      const rate = _rateLookup.get(g.sourceKey);
      if (rate) {
        const baseScore = (rate.sr * rate.dr) / 100;
        total +=
          Math.round(((baseScore * g.positions.size) / g.vc) * 10000) / 10000;
      }
    }
    return applyModuleSpawnRate(total, item.mod?.name || item.mapName);
  }

  for (const group of groupedByType.values()) {
    const _gName = group[0]?.mod?.group || '';
    const _rl = groupDropRateLookup.get(_gName) ?? new Map();
    group.sort((a, b) => {
      const scoreA = computeModuleScore(a, _rl);
      const scoreB = computeModuleScore(b, _rl);
      if (scoreA !== scoreB) return scoreB - scoreA;
      const hasVariantA = a.dots.some((d) => (d.variant_count ?? 1) > 1);
      const hasVariantB = b.dots.some((d) => (d.variant_count ?? 1) > 1);
      if (hasVariantA !== hasVariantB) return hasVariantA ? 1 : -1;
      if (a.dots.length !== b.dots.length) return b.dots.length - a.dots.length;
      const sy_a = a.mod?.size_y ?? 1;
      const sy_b = b.mod?.size_y ?? 1;
      if (sy_a !== sy_b) return sy_a - sy_b;
      const sx_a = a.mod?.size_x ?? 1;
      const sx_b = b.mod?.size_x ?? 1;
      return sx_a - sx_b;
    });
  }

  const groupOrder = GROUP_ORDER;
  const sortedGroups = [...groupedByType.entries()].sort(
    ([a, aItems], [b, bItems]) => {
      const _gA = aItems[0]?.mod?.group || '';
      const _gB = bItems[0]?.mod?.group || '';
      const _rlA = groupDropRateLookup.get(_gA) ?? new Map();
      const _rlB = groupDropRateLookup.get(_gB) ?? new Map();
      const totalA = aItems.reduce(
        (s, item) => s + computeModuleScore(item, _rlA),
        0
      );
      const totalB = bItems.reduce(
        (s, item) => s + computeModuleScore(item, _rlB),
        0
      );
      if (totalA !== totalB) return totalB - totalA;
      const dotA = aItems.reduce((s, item) => s + item.dots.length, 0);
      const dotB = bItems.reduce((s, item) => s + item.dots.length, 0);
      if (dotA !== dotB) return dotB - dotA;
      if (!a && !b) return 0;
      if (!a) return 1;
      if (!b) return -1;
      return groupOrder.indexOf(a) - groupOrder.indexOf(b);
    }
  );

  const recognitionTemplates: MapImageTemplate[] = [];
  const recognitionImageUrls = new Set<string>();
  for (const [, groupItems] of sortedGroups) {
    for (const item of groupItems) {
      const visibleDots = hideZeroRate
        ? item.dots.filter((dot) => {
            const groupName = item.mod?.group || '';
            const gdi = data?.group_drop_info?.[groupName];
            const entry = gdi?.find((candidate) =>
              matchesGroupEntry(candidate, dot.monster)
            );
            if (!entry) return true;
            if (modeFilter) return (entry.drop_rates[modeFilter] ?? 0) > 0;
            return hasAnyRate(entry.drop_rates);
          })
        : item.dots;
      const module = item.mod;
      if (!visibleDots.length || !module?.has_img) continue;
      const imageUrl = mapImageUrl(module);
      if (
        !isRecognizableMapImage(imageUrl) ||
        recognitionImageUrls.has(imageUrl)
      )
        continue;
      recognitionImageUrls.add(imageUrl);
      recognitionTemplates.push({
        id: item.mapName,
        url: imageUrl,
        label: t(module.translation_key, module.translation || item.mapName),
      });
    }
  }

  const visibleCountByMonster = new Map<string, number>();
  for (const m of resolvedMonsters) {
    const seenPos = new Set<string>();
    for (const c of m.coords) {
      if (hideZeroRate) {
        const mod = modules.get(c.map);
        const groupName = mod?.group || '';
        const gdi = data?.group_drop_info?.[groupName];
        const entry = gdi?.find((e) => matchesGroupEntry(e, m));
        if (entry) {
          if (modeFilter) {
            if ((entry.drop_rates[modeFilter] ?? 0) === 0) continue;
          } else {
            if (!hasAnyRate(entry.drop_rates)) continue;
          }
        }
      }
      const posKey = `${c.x},${c.y},${c.z}`;
      if (seenPos.has(posKey)) continue;
      seenPos.add(posKey);
      visibleCountByMonster.set(
        m.translation,
        (visibleCountByMonster.get(m.translation) ?? 0) + 1
      );
    }
  }
  const visibleMonsters = orderedMonsters.filter(
    (m) => (visibleCountByMonster.get(m.translation) ?? 0) > 0
  );
  let bottomCount = 0;
  const visibleMapsSet = new Set<string>();
  const bottomPosSet = new Set<string>();
  for (const [groupName, groupItems] of sortedGroups) {
    for (const item of groupItems) {
      for (const d of item.dots) {
        if (hideZeroRate) {
          const gdi = data?.group_drop_info?.[groupName];
          const entry = gdi?.find((e) => matchesGroupEntry(e, d.monster));
          if (entry) {
            if (modeFilter) {
              if ((entry.drop_rates[modeFilter] ?? 0) === 0) continue;
            } else {
              if (!hasAnyRate(entry.drop_rates)) continue;
            }
          }
        }
        const posKey = `${d.monster.translation}::${d.x},${d.y},${d.z}`;
        if (bottomPosSet.has(posKey)) continue;
        bottomPosSet.add(posKey);
        bottomCount++;
        visibleMapsSet.add(item.mapName);
      }
    }
  }
  const visibleCount = resolvedMonsters.filter(
    (m) => !hidden.has(m.translation)
  ).length;
  const rawLocationCount = resolvedMonsters.reduce(
    (count, monster) => count + monster.coords.length,
    0
  );
  const itemLabel = stripTrailingParenthetical(
    t(data.translation_key, data.translation || data.name)
  );
  const rarityLabel =
    currentSuffix && data.variant_rarity?.[currentSuffix]
      ? `(${t(data.variant_rarity[currentSuffix].translation_key, data.variant_rarity[currentSuffix].name)})`
      : '';
  const pageLabel = ut('ui.nav.lootdrops');
  const helmetTitle = `${itemLabel}${rarityLabel} -${pageLabel}`;
  const description = localizedSeoDescription(lang, dict, 'lootdrop', {
    name: itemLabel,
    sources: monsters.length || undefined,
    locations: rawLocationCount || undefined,
  });

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <DebugPanel
        buttons={[
          {
            label: ut('ui.common.debug_on'),
            activeLabel: ut('ui.common.debug_off'),
            active: debug,
            onClick: toggleDebug,
          },
        ]}
      />

      <Helmet>
        <title>
          {ssrLocalizedTitle() ?? `${helmetTitle} | ${ut('ui.brand.name')}`}
        </title>
        <meta name="description" content={description} />
        <meta name="keywords" content={ut('ui.seo.keywords')} />
        <meta
          property="og:title"
          content={
            ssrLocalizedTitle() ?? `${helmetTitle} | ${ut('ui.brand.name')}`
          }
        />
        <meta property="og:description" content={description} />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 28,
          margin: '0 0 8px',
        }}
      >
        {itemLabel}
        {currentSuffix && data.variant_rarity?.[currentSuffix] && (
          <span
            style={{
              color: getRarityColor(
                data.variant_rarity[currentSuffix],
                tokens.muted
              ),
              marginLeft: 8,
            }}
          >
            (
            {t(
              data.variant_rarity[currentSuffix].translation_key,
              data.variant_rarity[currentSuffix].name
            )}
            )
          </span>
        )}
        {' >> '}
        {resolvedMonsters
          .filter((m) => !hidden.has(m.translation))
          .map((m) => t(lootdropSourceTranslationKey(m), m.translation))
          .join(delimiter)}
        {resolvedMonsters.length - visibleCount > 0 && (
          <span style={{ color: tokens.muted, fontSize: 16 }}>
            {' '}
            (+{resolvedMonsters.length - visibleCount})
          </span>
        )}
        <span style={{ color: tokens.muted, fontSize: 14, marginLeft: 12 }}>
          {ut('ui.detail.coord_summary').replace(
            '{count}',
            String(resolvedMonsters.length)
          )}
        </span>
      </h1>

      <Disclaimer />

      {debug && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            justifyContent: 'center',
            margin: '15px 0',
            padding: 10,
            background: tokens.surface,
            borderRadius: 5,
            fontSize: 13,
            color: tokens.text,
            alignItems: 'center',
          }}
        >
          <span style={{ color: tokens.muted }}>
            {ut('ui.filter.drop_rate')}：
          </span>
          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            style={{
              background: tokens.bg,
              color: tokens.text,
              border: `1px solid ${tokens.border}`,
              borderRadius: 4,
              padding: '2px 6px',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            <option value="">{ut('ui.filter.all')}</option>
            <option value="PVE">{ut('ui.filter.pve')}</option>
            <option value="普通">{ut('ui.filter.normal')}</option>
            <option value="豪客赛">{ut('ui.filter.high_roller')}</option>
            <option value="逆袭赛">{ut('ui.filter.counter_raid')}</option>
          </select>
          <label style={{ cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={hideZeroRate}
              onChange={(e) => setHideZeroRate(e.target.checked)}
              style={{ marginRight: 3, cursor: 'pointer' }}
            />
            {ut('ui.filter.hide_zero_rate')}
          </label>
          <MapImageRecognition
            templates={recognitionTemplates}
            enabled={mapRecognitionEnabled}
            onEnabledChange={setMapRecognitionEnabled}
          />
        </div>
      )}

      {(() => {
        const qualitySet = new Set<string>();
        for (const m of resolvedMonsters) {
          for (const c of m.coords) {
            if (c.quality) qualitySet.add(c.quality);
          }
        }
        const hasQuality = qualitySet.size > 0;
        if (!hasQuality) return null;
        const QUALITY_CONFIG: Record<string, { label: string; color: string }> =
          {
            VeryLow: { label: ut('ui.rate.very_low'), color: '#9E9E9E' },
            Low: { label: ut('ui.rate.low'), color: '#BDBDBD' },
            Med: { label: ut('ui.rate.medium'), color: '#2ECC71' },
            High: { label: ut('ui.rate.high'), color: '#3498DB' },
          };
        return (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
              justifyContent: 'center',
              margin: '10px 0',
              padding: 10,
              background: tokens.surface,
              borderRadius: 5,
            }}
          >
            {[...qualitySet].sort().map((q) => {
              const cfg = QUALITY_CONFIG[q] ?? {
                label: q,
                color: tokens.muted,
              };
              const isActive = qualityFilter === q;
              return (
                <span
                  key={q}
                  onClick={() => setQualityFilter(isActive ? '' : q)}
                  style={{
                    padding: '6px 14px',
                    border: `2px solid ${cfg.color}`,
                    borderRadius: 5,
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 'bold',
                    color: isActive ? '#000' : tokens.text,
                    background: isActive ? cfg.color : 'transparent',
                    opacity: isActive ? 1 : 0.5,
                    transition: 'all 0.2s',
                  }}
                >
                  {cfg.label}
                </span>
              );
            })}
          </div>
        );
      })()}

      {data.variant_rarity && data.variants && (
        <VariantSwitch
          variantRarity={data.variant_rarity}
          suffixes={Object.keys(data.variants)}
          itemName={itemName}
          currentSuffix={currentSuffix}
        />
      )}

      {data.unavailableVariantSuffix && (
        <div
          style={{
            margin: '15px 0',
            padding: 10,
            textAlign: 'center',
            color: tokens.muted,
            background: tokens.surface,
            borderRadius: 5,
          }}
        >
          {ut('ui.detail.no_drop_rate')}
        </div>
      )}

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          justifyContent: 'center',
          margin: '15px 0',
          padding: 10,
          background: tokens.surface,
          borderRadius: 5,
        }}
      >
        <button
          onClick={() => {
            const allHidden = visibleMonsters.every((m) =>
              hidden.has(m.translation)
            );
            if (allHidden || hidden.size === visibleMonsters.length) {
              setHidden(new Set());
            } else {
              setHidden(new Set(visibleMonsters.map((m) => m.translation)));
            }
          }}
          style={{
            padding: '8px 15px',
            border: `2px solid ${tokens.border}`,
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 'bold',
            color: tokens.text,
            background: 'transparent',
            transition: 'all 0.2s',
          }}
        >
          {hidden.size === 0
            ? ut('ui.common.hide_all')
            : ut('ui.common.show_all')}
        </button>
        {visibleMonsters.map((m) => (
          <button
            key={m.translation}
            onClick={() => toggle(m.translation)}
            style={{
              padding: '8px 15px',
              border: `2px solid ${m.color}`,
              borderRadius: 5,
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 'bold',
              color: tokens.text,
              background: hidden.has(m.translation) ? 'transparent' : m.color,
              opacity: hidden.has(m.translation) ? 0.3 : 1,
              transition: 'all 0.2s',
            }}
          >
            {t(lootdropSourceTranslationKey(m), m.translation)} (
            {visibleCountByMonster.get(m.translation) ?? 0})
          </button>
        ))}
      </div>

      {debug && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 12,
            justifyContent: 'center',
            margin: '10px 0',
            padding: 10,
            background: tokens.surface,
            borderRadius: 5,
            fontSize: 14,
            color: tokens.muted,
          }}
        >
          <div
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 8,
              marginTop: 6,
              paddingTop: 8,
              borderTop: `1px solid ${tokens.border}`,
            }}
          >
            <label
              style={{ color: tokens.text, fontSize: 13, whiteSpace: 'nowrap' }}
            >
              {ut('ui.debug.default_threshold').replace(
                '{threshold}',
                String(threshold)
              )}
            </label>
            <input
              type="range"
              min={0}
              max={10}
              step={0.1}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              style={{ width: 200, cursor: 'pointer' }}
            />
            <input
              type="number"
              min={0}
              max={10}
              step={0.1}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              style={{
                width: 60,
                padding: '2px 4px',
                fontSize: 13,
                background: tokens.bg,
                color: tokens.text,
                border: `1px solid ${tokens.border}`,
                borderRadius: 3,
              }}
            />
            <span style={{ color: tokens.muted, fontSize: 11 }}>
              {ut('ui.debug.threshold_hint').replace(
                '{threshold}',
                String(threshold)
              )}
            </span>
          </div>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gap: 6,
          gridTemplateColumns: 'repeat(4, 1fr)',
        }}
      >
        {sortedGroups.map(([groupName, groupItems]) => (
          <SectionHeader
            key={groupName}
            groupName={groupName}
            hasVisible={
              hideZeroRate
                ? groupItems.some(({ dots }) =>
                    dots.some((d) => {
                      const gdi = data?.group_drop_info?.[groupName];
                      const entry = gdi?.find((e) =>
                        matchesGroupEntry(e, d.monster)
                      );
                      if (!entry) return true;
                      if (modeFilter)
                        return (entry.drop_rates[modeFilter] ?? 0) > 0;
                      return hasAnyRate(entry.drop_rates);
                    })
                  )
                : groupItems.length > 0
            }
          >
            {groupName && (
              <div
                key={`h-${groupName}`}
                style={{
                  gridColumn: '1 / -1',
                  padding: '5px 0',
                  marginTop: 10,
                  borderBottom: dark
                    ? '2px solid #FFC107'
                    : '2px solid #F57F17',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: 10,
                    flexWrap: 'wrap',
                    color: dark ? '#FFC107' : '#F57F17',
                  }}
                >
                  <span
                    style={{
                      fontSize: 22,
                      fontWeight: 'bold',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {formatGroupLabel(groupItems[0]?.mod, t, ut) || groupName}
                  </span>
                  {data?.group_drop_info?.[groupName] && (
                    <ReferenceDropRates
                      entries={data.group_drop_info[groupName]!.filter(
                        (info) => {
                          const m = resolvedMonsters.find((source) =>
                            matchesGroupEntry(info, source)
                          );
                          return m && !hidden.has(m.translation);
                        }
                      )}
                      modeFilter={modeFilter}
                      style={{
                        fontSize: 13,
                        fontWeight: 'normal',
                        color: tokens.muted,
                      }}
                    />
                  )}
                </div>
              </div>
            )}
            {groupItems.map(({ mapName, mod, dots: rawDots }) => {
              const dots = hideZeroRate
                ? rawDots.filter((d) => {
                    const gdi = data?.group_drop_info?.[groupName];
                    const entry = gdi?.find((e) =>
                      matchesGroupEntry(e, d.monster)
                    );
                    if (!entry) return true;
                    if (modeFilter)
                      return (entry.drop_rates[modeFilter] ?? 0) > 0;
                    return hasAnyRate(entry.drop_rates);
                  })
                : rawDots;
              if (dots.length === 0) return null;
              const sx = mod?.size_x ?? 1;
              const sy = mod?.size_y ?? 1;
              const baseRange = mod?.range || Math.max(sx, sy) * 1600 || 1600;
              const adj = myGetAdj(mapName, mod);
              const range = baseRange + adj.range || 1600;
              const offX = (mod?.offset_x ?? 0) + adj.x;
              const offY = (mod?.offset_y ?? 0) + adj.y;
              return (
                <div
                  key={mapName}
                  ref={(el) => mapRef(mapName, el)}
                  style={{
                    minWidth: 0,
                    gridColumn: sx >= 2 ? `span ${sx}` : undefined,
                    gridRow: sy >= 2 ? `span ${sy}` : undefined,
                    background: tokens.surface,
                    border: `1px solid ${tokens.border}`,
                    borderRadius: 5,
                    padding: 8,
                  }}
                >
                  <h3
                    style={{
                      margin: '0 0 6px 0',
                      fontSize: 22,
                      color: tokens.accent,
                      textAlign: 'center',
                      width: '100%',
                      lineHeight: 1.3,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {t(
                      mod?.translation_key,
                      mod?.translation || mod?.name || mapName
                    )}
                    {getRareModuleSpawnRate(mod?.name || mapName) > 0 && (
                      <>
                        {' '}
                        <span
                          style={{
                            marginLeft: 8,
                            fontSize: 13,
                            fontWeight: 'normal',
                            color: tokens.muted,
                          }}
                        >
                          {ut('ui.detail.module_spawn_rate').replace(
                            '{rate}',
                            String(getRareModuleSpawnRate(mod?.name || mapName))
                          )}
                        </span>
                      </>
                    )}
                    {debug && (
                      <span style={{ color: tokens.muted, fontSize: 11 }}>
                        {' '}
                        ({mapName})
                      </span>
                    )}
                  </h3>
                  {debug && (
                    <div
                      style={{
                        fontSize: 10,
                        color: tokens.muted,
                        textAlign: 'center',
                        marginBottom: 4,
                      }}
                    >
                      {mod?.img_name || mod?.sl_base_name || mapName}.webp |
                      {ut('ui.debug.map_summary')
                        .replace('{count}', String(dots.length))
                        .replace('{range}', String(range))}
                    </div>
                  )}
                  {debug && (
                    <div
                      style={{
                        fontSize: 10,
                        color: tokens.muted,
                        textAlign: 'center',
                        marginBottom: 4,
                        lineHeight: 1.4,
                      }}
                    >
                      {dots[0]?.file || ''}
                      <br />
                      {ut('ui.debug.transform')
                        .replace('{rotation}', String(mod?.rotate ?? 0))
                        .replace('{x}', String(mod?.offset_x ?? 0))
                        .replace('{y}', String(mod?.offset_y ?? 0))
                        .replace('{sx}', String(sx))
                        .replace('{sy}', String(sy))}
                    </div>
                  )}
                  {debug && (
                    <div
                      style={{
                        fontSize: 11,
                        color: tokens.muted,
                        marginBottom: 4,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 3,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          gap: 4,
                          alignItems: 'center',
                        }}
                      >
                        <span style={{ color: tokens.muted }}>
                          {ut('ui.debug.range')}
                        </span>
                        <button
                          onClick={() =>
                            setAdj(
                              mapName,
                              'range',
                              Math.round(range / 2) - baseRange
                            )
                          }
                          style={ctrlBtn}
                        >
                          ÷2
                        </button>
                        <input
                          type="number"
                          value={range}
                          onChange={(e) =>
                            setAdj(
                              mapName,
                              'range',
                              Number(e.target.value) - baseRange
                            )
                          }
                          style={ctrlInput}
                          step={100}
                        />
                        <button
                          onClick={() =>
                            setAdj(mapName, 'range', range * 2 - baseRange)
                          }
                          style={ctrlBtn}
                        >
                          x2
                        </button>
                        <span
                          style={{
                            color: tokens.muted,
                            fontSize: 12,
                            marginLeft: 4,
                          }}
                        >
                          ↻{adj.rotate}
                        </span>
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          gap: 4,
                          alignItems: 'center',
                        }}
                      >
                        <span style={{ color: tokens.muted }}>
                          {ut('ui.debug.offset')}
                        </span>
                        <button
                          onClick={() => setAdj(mapName, 'y', adj.y - 50)}
                          style={ctrlBtn}
                        >
                          ↑
                        </button>
                        <button
                          onClick={() => setAdj(mapName, 'y', adj.y + 50)}
                          style={ctrlBtn}
                        >
                          ↓
                        </button>
                        <button
                          onClick={() => setAdj(mapName, 'x', adj.x - 50)}
                          style={ctrlBtn}
                        >
                          ←
                        </button>
                        <button
                          onClick={() => setAdj(mapName, 'x', adj.x + 50)}
                          style={ctrlBtn}
                        >
                          →
                        </button>
                        <span style={{ color: tokens.muted, marginLeft: 8 }}>
                          X:
                        </span>
                        <input
                          type="number"
                          value={offX}
                          onChange={(e) =>
                            setAdj(
                              mapName,
                              'x',
                              Number(e.target.value) - (mod?.offset_x ?? 0)
                            )
                          }
                          style={ctrlInput}
                          step={10}
                        />
                        <span style={{ color: tokens.muted }}>Y:</span>
                        <input
                          type="number"
                          value={offY}
                          onChange={(e) =>
                            setAdj(
                              mapName,
                              'y',
                              Number(e.target.value) - (mod?.offset_y ?? 0)
                            )
                          }
                          style={ctrlInput}
                          step={10}
                        />
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          gap: 4,
                          alignItems: 'center',
                        }}
                      >
                        <button
                          onClick={() =>
                            setAdj(
                              mapName,
                              'rotate',
                              ((adj.rotate ?? 0) + 90) % 360
                            )
                          }
                          style={ctrlBtn}
                        >
                          ↻ {ut('ui.debug.rotate')}
                        </button>
                        <button
                          onClick={() =>
                            setAdj(mapName, 'mirrorX', !adj.mirrorX)
                          }
                          style={{
                            ...ctrlBtn,
                            background: adj.mirrorX ? '#4CAF50' : '#555',
                          }}
                        >
                          ⇄ {ut('ui.debug.mirror_horizontal')}
                        </button>
                        <button
                          onClick={() =>
                            setAdj(mapName, 'mirrorY', !adj.mirrorY)
                          }
                          style={{
                            ...ctrlBtn,
                            background: adj.mirrorY ? '#4CAF50' : '#555',
                          }}
                        >
                          ⇅ {ut('ui.debug.mirror_vertical')}
                        </button>
                        <button
                          onClick={() =>
                            setAdjOffsets((prev) => {
                              const n = { ...prev };
                              delete n[mapName];
                              return n;
                            })
                          }
                          style={ctrlBtn}
                        >
                          ↺ {ut('ui.debug.reset')}
                        </button>
                      </div>
                    </div>
                  )}
                  {visibleMaps.has(mapName) ? (
                    <MapPanel
                      imageSrc={mapImageUrl(mod)}
                      sx={sx}
                      sy={sy}
                      dots={dots.map((d) => ({
                        x: d.x,
                        y: d.y,
                        z: d.z,
                        color: d.monster.color,
                        title: d.monster.translation,
                      }))}
                      offX={offX}
                      offY={offY}
                      adj={adj}
                      range={range}
                    />
                  ) : (
                    <div
                      style={{
                        aspectRatio: `${sx} / ${sy}`,
                        backgroundColor: tokens.bg,
                        border: `1px solid ${tokens.border}`,
                        borderRadius: 4,
                      }}
                    />
                  )}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '4px 10px',
                      justifyContent: 'center',
                      marginTop: 5,
                      fontSize: 13,
                      color: tokens.text,
                      alignItems: 'center',
                    }}
                  >
                    {[
                      ...new Set(dots.map((d) => lootdropSourceKey(d.monster))),
                    ].map((sourceId) => {
                      const m = resolvedMonsters.find(
                        (source) => lootdropSourceKey(source) === sourceId
                      )!;
                      const tl = m.translation;
                      const mDots = dots.filter(
                        (d) => lootdropSourceKey(d.monster) === sourceId
                      );
                      if (hideZeroRate) {
                        const gdi = data?.group_drop_info?.[groupName];
                        const entry = gdi?.find((e) => matchesGroupEntry(e, m));
                        if (entry) {
                          if (
                            modeFilter &&
                            (entry.drop_rates[modeFilter] ?? 0) === 0
                          )
                            return null;
                          if (!modeFilter && !hasAnyRate(entry.drop_rates))
                            return null;
                        }
                      }
                      // 取该怪物在此模块中的 spawn_rate（所有点通常相同，取第一个非默认值）
                      const sr = mDots.find(
                        (d) => d.spawn_rate != null
                      )?.spawn_rate;
                      const dr = m.drop_rates;
                      const filteredDr =
                        dr && modeFilter && dr[modeFilter] != null
                          ? { [modeFilter]: dr[modeFilter] }
                          : dr;
                      const hasRates =
                        filteredDr && Object.keys(filteredDr).length > 0;
                      return (
                        <span
                          key={sourceId}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 3,
                            flexWrap: 'wrap',
                          }}
                        >
                          <span
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: '50%',
                              background: m.color,
                              flexShrink: 0,
                            }}
                          ></span>
                          <span
                            style={{ cursor: 'pointer' }}
                            onClick={() => toggle(tl)}
                          >
                            {t(lootdropSourceTranslationKey(m), m.translation)}
                          </span>
                          {sr != null && sr !== 100 && (
                            <span
                              style={{ color: tokens.accent, fontSize: 12 }}
                            >
                              {sr}%
                            </span>
                          )}
                          {hasRates && (
                            <span style={{ color: tokens.muted, fontSize: 12 }}>
                              (
                              {Object.entries(filteredDr!)
                                .map(
                                  ([mode, rate]) =>
                                    `[${dropRateModeLabel(mode, t, ut)}:${rate}%]`
                                )
                                .join('')}
                              )
                            </span>
                          )}
                          <span style={{ color: tokens.muted }}>
                            {(() => {
                              const linkerGroups = new Map<
                                string,
                                {
                                  dots: typeof mDots;
                                  poolSize: number;
                                  poolEntries: VariantNameEntry[];
                                }
                              >();
                              for (const d of mDots) {
                                const sgp = d.sub_group_parent;
                                const gp = d.group_parent;
                                if (!sgp || !gp) continue;
                                const key = `${gp}::${sgp}`;
                                if (!linkerGroups.has(key)) {
                                  linkerGroups.set(key, {
                                    dots: [],
                                    poolSize: d.sub_pool_size ?? 0,
                                    poolEntries: d.sub_pool_entries ?? [],
                                  });
                                }
                                linkerGroups.get(key)!.dots.push(d);
                              }
                              const linkerKeys = new Set<string>();
                              for (const [, g] of linkerGroups) {
                                for (const d of g.dots) {
                                  linkerKeys.add(`${d.x},${d.y},${d.z}`);
                                }
                              }
                              const nonLinkerDots = mDots.filter(
                                (d) => !linkerKeys.has(`${d.x},${d.y},${d.z}`)
                              );
                              const varDots = nonLinkerDots.filter(
                                (d) => d.variant_count && d.variant_count > 1
                              );
                              const regDots = nonLinkerDots.filter(
                                (d) => !d.variant_count || d.variant_count <= 1
                              );
                              const dedupPos = (
                                arr: typeof regDots,
                                gp?: string
                              ) => {
                                const seen = new Set<string>();
                                return arr.filter((d) => {
                                  if (gp && d.group_parent !== gp) return false;
                                  const k = `${d.x},${d.y},${d.z}`;
                                  if (seen.has(k)) return false;
                                  seen.add(k);
                                  return true;
                                });
                              };
                              const parts: string[] = [];
                              for (const [, g] of linkerGroups) {
                                const uniquePos = new Set(
                                  g.dots.map((d) => `${d.x},${d.y},${d.z}`)
                                ).size;
                                parts.push(
                                  `(${g.poolEntries.map((entry) => t(entry.translation_key, entry.name)).join(ut('ui.location.map_sep'))}${ut('ui.detail.pool_select').replace('{count}', String(g.poolSize)).replace('{positions}', String(uniquePos))}${uniquePos > 1 ? ` · ${ut('ui.detail.pool_positions').replace('{count}', String(uniquePos)).replace('{select}', '1')}` : ''})`
                                );
                              }
                              const dedupedReg = dedupPos(regDots);
                              if (dedupedReg.length > 0) {
                                parts.push(
                                  `(${ut('ui.detail.position_count').replace('{count}', String(dedupedReg.length))})`
                                );
                              }
                              if (varDots.length > 0) {
                                const names = varDots[0].variant_names ?? [];
                                const varGps = [
                                  ...new Set(
                                    varDots
                                      .map((d) => d.group_parent)
                                      .filter(Boolean)
                                  ),
                                ];
                                const varPosCounts = varGps.map((gp) => ({
                                  gp,
                                  count: dedupPos(varDots, gp).length,
                                }));
                                const totalVarPos = varPosCounts.reduce(
                                  (s, v) => s + v.count,
                                  0
                                );
                                if (names.length > 0) {
                                  if (totalVarPos > 1) {
                                    parts.push(
                                      `(${ut('ui.detail.pool_positions')
                                        .replace('{count}', String(totalVarPos))
                                        .replace(
                                          '{select}',
                                          String(varDots[0].variant_count)
                                        )})`
                                    );
                                  } else {
                                    const nameStr = names
                                      .map((entry) =>
                                        t(entry.translation_key, entry.name)
                                      )
                                      .join(ut('ui.location.map_sep'));
                                    parts.push(
                                      `(${nameStr}${ut('ui.detail.pool_select')
                                        .replace(
                                          '{count}',
                                          String(names.length)
                                        )
                                        .replace('{positions}', '1')})`
                                    );
                                  }
                                } else {
                                  parts.push(
                                    varGps.length === 1
                                      ? `(${ut('ui.detail.pool_positions')
                                          .replace(
                                            '{count}',
                                            String(totalVarPos)
                                          )
                                          .replace('{select}', '1')})`
                                      : `(${ut('ui.detail.position_count').replace('{count}', String(totalVarPos))})`
                                  );
                                }
                              }
                              return parts.join(' ');
                            })()}
                          </span>
                        </span>
                      );
                    })}
                  </div>
                  <CompositeRate
                    rate={computeModuleScore(
                      { mod, dots },
                      groupDropRateLookup.get(groupName) ?? new Map()
                    )}
                  />
                </div>
              );
            })}
          </SectionHeader>
        ))}
      </div>

      {debug &&
        (() => {
          const rows = resolvedMonsters.flatMap((m) =>
            m.coords.map((c, j) => {
              const mod = modules.get(c.map);
              const g = mod?.group || '';
              const rowKey = `${m.translation}-${j}`;
              return {
                key: rowKey,
                group: formatGroupLabel(mod, t, ut) || g,
                monster: {
                  name: m.name,
                  translation: m.translation,
                  color: m.color,
                  onToggle: () => toggle(m.translation),
                },
                file: c.file,
                mapName: c.map,
                mapLabel: t(mod?.translation_key, mod?.translation || c.map),
                label: c.label || '',
                x: c.x,
                y: c.y,
                z: c.z,
                hidden: hidden.has(m.translation) || hiddenRows.has(rowKey),
              };
            })
          );
          function batchToggle(pred: (r: (typeof rows)[number]) => boolean) {
            const matched = rows.filter(pred);
            if (matched.length === 0) return;
            const allHidden = matched.every((r) => r.hidden);
            for (const r of matched) {
              const mTl = r.monster?.translation;
              if (allHidden) {
                if (mTl && hidden.has(mTl)) {
                  toggle(mTl);
                }
                toggleRow(r.key, true);
              } else {
                toggleRow(r.key, false);
              }
            }
          }
          return (
            <DebugCoordTable
              rows={rows}
              onToggleRow={toggleRow}
              onToggleGroup={(gk) => batchToggle((r) => r.group === gk)}
              onToggleMarkName={(name) =>
                batchToggle((r) => r.monster?.name === name)
              }
              onToggleFile={(f) => batchToggle((r) => r.file === f)}
              onToggleMap={(mn) => batchToggle((r) => r.mapName === mn)}
              onToggleLabel={(l) => batchToggle((r) => r.label === l)}
              showMonster
            />
          );
        })()}

      <div
        style={{
          marginTop: 10,
          padding: 10,
          background: tokens.surface,
          borderRadius: 5,
          fontSize: 15,
          textAlign: 'center',
          color: tokens.muted,
        }}
      >
        <LocationStats
          count={bottomCount}
          mapKeys={[...visibleMapsSet]}
          modules={modules}
        />
      </div>
    </div>
  );
}
