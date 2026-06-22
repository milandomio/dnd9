import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useDataVersion } from '../hooks/useDataVersion';
import { useDebug } from '../hooks/useDebug';
import { useTheme } from '../hooks/useTheme';
import { useSSRData } from '../context/SSRDataContext';
import { useDungeonModules } from '../hooks/useDungeonModules';
import type { DungeonModule } from '../types/data';
import {
  getAdj,
  useCtrlBtn,
  useCtrlInput,
  type AdjState,
} from '../components/MapDebug';
import Disclaimer from '../components/Disclaimer';
import DebugCoordTable from '../components/DebugCoordTable';
import MapPanel from '../components/MapPanel';

interface LootdropCoord {
  x: number;
  y: number;
  z: number;
  map: string;
  file: string;
  version: string;
  label?: string;
  spawn_rate?: number;
  variant_count?: number;
  variant_names?: string[];
}

interface LootdropMonster {
  name: string;
  translation: string;
  color: string;
  coords: LootdropCoord[];
  drop_rates?: Record<string, number>;
  max_score?: number;
}

interface GroupDropInfo {
  translation: string;
  spawn_rate: number;
  spawn_rates?: Record<string, number>;
  drop_rates: Record<string, number>;
}

interface LootdropItem {
  name: string;
  translation: string;
  monsters: LootdropMonster[];
  group_drop_info?: Record<string, GroupDropInfo[]>;
}

const GROUP_LABELS: Record<string, string> = {
  Crypt: '废墟2层地牢',
  FireDeep: '哥布林洞穴2层',
  GoblinCave: '哥布林洞穴1层',
  IceAbyss: '冰图2层',
  IceCavern: '冰图1层',
  Inferno: '废墟3层炼狱',
  Ruins: '废墟1层',
  ShipGraveyard: '水图',
};

export default function LootdropDetailPage() {
  const { name } = useParams<{ name: string }>();
  const dataKey = `lootdrops/${name ? decodeURIComponent(name) : ''}`;
  const ssrData = useSSRData<{ item: LootdropItem; modules: DungeonModule[] }>(
    dataKey
  );
  const [data, setData] = useState<LootdropItem | null>(
    ssrData?.item?.monsters ? ssrData.item : null
  );
  const dataVersion = useDataVersion();

  function defaultHidden(
    monsters: LootdropMonster[],
    threshold: number
  ): Set<string> {
    const init = new Set<string>();
    for (const m of monsters) {
      if (m.name.endsWith('_Elite')) continue;
      const sc = m.max_score;
      if (sc == null || sc < 0) continue;
      if (sc < threshold) init.add(m.name);
    }
    return init;
  }
  // Prefer SSR-provided modules to avoid untranslated names during SSR/hydration
  const ssrModulesMap = useMemo(() => {
    if (!ssrData?.modules) return null;
    const mm = new Map<string, DungeonModule>();
    for (const m of ssrData.modules) {
      const names = m.names || [m.name];
      names.forEach((n) => mm.set(n, m));
      mm.set(m.sl_base_name, m);
      if (m.all_sl_base_names) {
        m.all_sl_base_names.forEach((sl) => mm.set(sl, m));
      }
    }
    return mm;
  }, [ssrData]);
  const { modules: fetchedModules } = useDungeonModules();
  const modules = ssrModulesMap ?? fetchedModules;
  const [hidden, setHidden] = useState<Set<string>>(() =>
    ssrData?.item?.monsters
      ? defaultHidden(ssrData.item.monsters, 2.5)
      : new Set()
  );
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set()); // per-coord toggle: \"monsterName-index\"
  const [threshold, setThreshold] = useState(2.5);
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();
  const { tokens, dark } = useTheme();
  const ctrlBtn = useCtrlBtn();
  const ctrlInput = useCtrlInput();

  useEffect(() => {
    if (!name) return;
    if (ssrData?.item?.monsters) {
      setData(ssrData.item);
      setHidden(defaultHidden(ssrData.item.monsters, 2.5));
      return;
    }
    setData(null);
    setHidden(new Set());
    const lootUrl = dataVersion
      ? `/data/json/lootdrops/${decodeURIComponent(name)}.json?v=${dataVersion}`
      : `/data/json/lootdrops/${decodeURIComponent(name)}.json`;
    fetch(lootUrl)
      .then<LootdropItem>((r) => r.json())
      .then((item) => {
        setData(item);
        setHidden(defaultHidden(item.monsters, 2.5));
      })
      .catch(console.error);
  }, [name, ssrData, dataVersion]);

  // 在调试模式下实时响应阈值变化
  useEffect(() => {
    if (!data?.monsters) return;
    setHidden(defaultHidden(data.monsters, threshold));
  }, [threshold]);

  const [visibleMaps, setVisibleMaps] = useState<Set<string>>(new Set());
  const observerRef = useRef<IntersectionObserver | null>(null);
  const imageUrlsRef = useRef(new Map<string, string>());
  const [, setImageUrlsTick] = useState(0);
  const controllersRef = useRef(new Map<string, AbortController>());
  const timersRef = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  /** Schedule a delayed fetch; cancel if map leaves viewport before timeout */
  const scheduleFetch = useCallback(
    (mn: string) => {
      if (
        imageUrlsRef.current.has(mn) ||
        controllersRef.current.has(mn) ||
        timersRef.current.has(mn)
      )
        return;
      const timer = setTimeout(() => {
        timersRef.current.delete(mn);
        const mod = modules.get(mn);
        const imgName = mod?.img_name || mod?.sl_base_name || 'RareModule_1x1';
        const ctrl = new AbortController();
        controllersRef.current.set(mn, ctrl);
        fetch(`/data/img/${imgName}.webp`, { signal: ctrl.signal })
          .then((r) => r.blob())
          .then((blob) => {
            const url = URL.createObjectURL(blob);
            imageUrlsRef.current.set(mn, url);
            controllersRef.current.delete(mn);
            setImageUrlsTick((v) => v + 1);
          })
          .catch(() => {
            controllersRef.current.delete(mn);
          });
      }, 500);
      timersRef.current.set(mn, timer);
    },
    [modules]
  );

  const mapRef = useCallback(
    (mapName: string, el: HTMLDivElement | null) => {
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
                  scheduleFetch(mn);
                } else if (!imageUrlsRef.current.has(mn)) {
                  next.delete(mn);
                  // Cancel pending timer (never started download)
                  const tm = timersRef.current.get(mn);
                  if (tm) {
                    clearTimeout(tm);
                    timersRef.current.delete(mn);
                  }
                  // Abort in-flight fetch (download already started)
                  const ctrl = controllersRef.current.get(mn);
                  if (ctrl) {
                    ctrl.abort();
                    controllersRef.current.delete(mn);
                  }
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
    },
    [scheduleFetch]
  );

  // Cleanup: revoke blob URLs, abort fetches, clear timers on unmount
  useEffect(() => {
    return () => {
      for (const t of timersRef.current.values()) clearTimeout(t);
      for (const ctrl of controllersRef.current.values()) ctrl.abort();
      for (const url of imageUrlsRef.current.values()) URL.revokeObjectURL(url);
    };
  }, []);

  const monsters = data?.monsters ?? [];
  const orderedMonsters = useMemo(() => {
    return [...monsters].sort(
      (a, b) => (b.max_score ?? -1) - (a.max_score ?? -1)
    );
  }, [monsters]);

  if (!data)
    return (
      <div style={{ textAlign: 'center', color: '#ff6b6b', marginTop: 100 }}>
        数据加载中...
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
      mod: DungeonModule | undefined;
      dots: {
        monster: LootdropMonster;
        x: number;
        y: number;
        z: number;
        file: string;
        idx: number;
        spawn_rate?: number;
        variant_count?: number;
        variant_names?: string[];
      }[];
    }
  >();
  for (const m of monsters) {
    m.coords.forEach((c, j) => {
      if (hidden.has(m.name) || hiddenRows.has(`${m.name}-${j}`)) return;
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

  for (const group of groupedByType.values()) {
    group.sort((a, b) => {
      const sy_a = a.mod?.size_y ?? 1;
      const sy_b = b.mod?.size_y ?? 1;
      const sx_a = a.mod?.size_x ?? 1;
      const sx_b = b.mod?.size_x ?? 1;
      if (sy_a !== sy_b) return sy_a - sy_b;
      if (sx_a !== sx_b) return sx_a - sx_b;
      return b.dots.length - a.dots.length;
    });
  }

  const groupOrder = Object.keys(GROUP_LABELS);
  const sortedGroups = [...groupedByType.entries()].sort(
    ([a, aItems], [b, bItems]) => {
      const totalA = aItems.reduce((s, item) => s + item.dots.length, 0);
      const totalB = bItems.reduce((s, item) => s + item.dots.length, 0);
      if (totalA !== totalB) return totalB - totalA;
      if (!a && !b) return 0;
      if (!a) return 1;
      if (!b) return -1;
      return groupOrder.indexOf(a) - groupOrder.indexOf(b);
    }
  );

  const totalCoords = monsters.reduce(
    (s, m) => s + (hidden.has(m.name) ? 0 : m.coords.length),
    0
  );
  const visibleCount = monsters.filter((m) => !hidden.has(m.name)).length;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <button
        onClick={toggleDebug}
        style={{
          position: 'fixed',
          top: 20,
          right: 20,
          padding: '4px 16px',
          background: debug ? '#4CAF50' : '#FFC107',
          color: debug ? '#fff' : '#000',
          border: debug ? '2px solid #388E3C' : '2px solid #FF9800',
          borderRadius: 6,
          cursor: 'pointer',
          fontSize: 13,
          fontWeight: 'bold',
          zIndex: 9999,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        }}
      >
        {debug ? '退出调试' : '显示调试信息'}
      </button>

      <Helmet>
        <title>
          {data.translation || data.name} 掉落来源 | DarkFindV5游戏导航
        </title>
        <meta
          name="description"
          content={`${data.translation || data.name} 由 ${visibleCount} 个怪物掉落，共 ${totalCoords} 个位置点。`}
        />
        <meta
          property="og:title"
          content={`${data.translation || data.name} 掉落来源 | DarkFindV5`}
        />
        <meta
          property="og:description"
          content={`${data.translation || data.name} 由 ${visibleCount} 个怪物掉落`}
        />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 28,
          margin: '0 0 8px',
        }}
      >
        {data.translation} &gt;&gt;{' '}
        {monsters
          .filter((m) => !hidden.has(m.name))
          .map((m) => m.translation)
          .join('、')}
        {monsters.length - visibleCount > 0 && (
          <span style={{ color: tokens.muted, fontSize: 16 }}>
            {' '}
            (+{monsters.length - visibleCount})
          </span>
        )}
        <span style={{ color: tokens.muted, fontSize: 14, marginLeft: 12 }}>
          {monsters.length}种坐标汇总
        </span>
      </h1>

      <Disclaimer />

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
            const allHidden = monsters.every((m) => hidden.has(m.name));
            if (allHidden || hidden.size === monsters.length) {
              setHidden(new Set());
            } else {
              setHidden(new Set(monsters.map((m) => m.name)));
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
          {hidden.size === 0 ? '隐藏全部' : '全部显示'}
        </button>
        {orderedMonsters.map((m) => (
          <button
            key={m.name}
            onClick={() => toggle(m.name)}
            style={{
              padding: '8px 15px',
              border: `2px solid ${m.color}`,
              borderRadius: 5,
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 'bold',
              color: tokens.text,
              background: hidden.has(m.name) ? 'transparent' : m.color,
              opacity: hidden.has(m.name) ? 0.3 : 1,
              transition: 'all 0.2s',
            }}
          >
            {m.translation} ({m.coords.length})
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
              默认显示阈值（乘积%）：{threshold}%
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
              spawn_rate × 豪客赛爆率 ≥ {threshold}% 则默认显示
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
          <>
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
                    {GROUP_LABELS[groupName] || groupName}
                  </span>
                  {data?.group_drop_info?.[groupName] && (
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 'normal',
                        color: tokens.muted,
                      }}
                    >
                      参考爆率：
                      {data.group_drop_info[groupName]!.filter((info) => {
                        const m = monsters.find(
                          (x) => x.translation === info.translation
                        );
                        return m && !hidden.has(m.name);
                      }).map((info, gi) => (
                        <span
                          key={gi}
                          style={{
                            display: 'inline-block',
                            marginRight: 8,
                          }}
                        >
                          {info.translation}
                          {info.spawn_rates &&
                          Object.keys(info.spawn_rates).length > 1
                            ? Object.entries(info.drop_rates)
                                .map(([mode, rate]) => {
                                  const sRate = info.spawn_rates![mode];
                                  return sRate != null
                                    ? `[${mode}:${sRate}%×${rate}%]`
                                    : `[${mode}:${rate}%]`;
                                })
                                .join('')
                            : `${info.spawn_rate}%${Object.entries(
                                info.drop_rates
                              )
                                .map(([mode, rate]) => `[${mode}:${rate}%]`)
                                .join('')}`}
                        </span>
                      ))}
                    </span>
                  )}
                </div>
              </div>
            )}
            {groupItems.map(({ mapName, mod, dots }) => {
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
                    {mod?.translation || mapName}
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
                      找到 {dots.length} 个位置 | 范围: ±{range}
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
                      旋转:{mod?.rotate ?? 0} 偏移:({mod?.offset_x ?? 0},
                      {mod?.offset_y ?? 0}) 大小:{sx}x{sy}
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
                        <span style={{ color: tokens.muted }}>范围:</span>
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
                        <span style={{ color: tokens.muted }}>偏移:</span>
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
                          ↻ 旋转
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
                          ⇄ 左右
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
                          ⇅ 上下
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
                          ↺ 重置
                        </button>
                      </div>
                    </div>
                  )}
                  {visibleMaps.has(mapName) ? (
                    <MapPanel
                      imageSrc={imageUrlsRef.current.get(mapName)}
                      imgName={
                        mod?.img_name || mod?.sl_base_name || 'RareModule_1x1'
                      }
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
                    {[...new Set(dots.map((d) => d.monster.name))].map((mn) => {
                      const m = monsters.find((x) => x.name === mn)!;
                      const mDots = dots.filter((d) => d.monster.name === mn);
                      // 取该怪物在此模块中的 spawn_rate（所有点通常相同，取第一个非默认值）
                      const sr = mDots.find(
                        (d) => d.spawn_rate != null
                      )?.spawn_rate;
                      const dr = m.drop_rates;
                      const hasRates = dr && Object.keys(dr).length > 0;
                      return (
                        <span
                          key={mn}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 3,
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
                            onClick={() => toggle(mn)}
                          >
                            {m.translation}
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
                              {Object.entries(dr!)
                                .map(([mode, rate]) => `[${mode}:${rate}%]`)
                                .join('')}
                              )
                            </span>
                          )}
                          <span style={{ color: tokens.muted }}>
                            {(() => {
                              const vcDot = mDots.find(
                                (d) => d.variant_count && d.variant_count > 1
                              );
                              if (vcDot) {
                                const names = vcDot.variant_names ?? [];
                                if (names.length > 0) {
                                  return `(${names.join('、')}${vcDot.variant_count}种选1)`;
                                }
                                const uniquePositions = new Set(
                                  mDots.map((d) => `${d.x},${d.y},${d.z}`)
                                );
                                return `(${uniquePositions.size}点选1)`;
                              }
                              return `(${mDots.length}点)`;
                            })()}
                          </span>
                        </span>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </>
        ))}
      </div>

      {debug &&
        (() => {
          const rows = monsters.flatMap((m) =>
            m.coords.map((c, j) => {
              const mod = modules.get(c.map);
              const g = mod?.group || '';
              const rowKey = `${m.name}-${j}`;
              return {
                key: rowKey,
                group: GROUP_LABELS[g] || g,
                monster: {
                  name: m.name,
                  translation: m.translation,
                  color: m.color,
                  onToggle: () => toggle(m.name),
                },
                file: c.file,
                mapName: c.map,
                mapLabel: mod?.translation || c.map,
                label: c.label || '',
                x: c.x,
                y: c.y,
                z: c.z,
                hidden: hidden.has(m.name) || hiddenRows.has(rowKey),
              };
            })
          );
          function batchToggle(pred: (r: (typeof rows)[number]) => boolean) {
            const matched = rows.filter(pred);
            if (matched.length === 0) return;
            const allHidden = matched.every((r) => r.hidden);
            for (const r of matched) {
              const mName = r.monster?.name;
              if (allHidden) {
                if (mName && hidden.has(mName)) {
                  toggle(mName);
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
        <strong>位置统计：共 {totalCoords} 个位置点</strong>
        <br />
        <strong>包含地图：</strong>{' '}
        {[...new Set([...mapGroups.keys()])]
          .map((k) => modules.get(k)?.translation || k)
          .join('、')}
      </div>
    </div>
  );
}
