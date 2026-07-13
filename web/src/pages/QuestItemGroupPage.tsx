import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
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

interface Coord {
  x: number;
  y: number;
  z: number;
  map: string;
  file: string;
  version: string;
  label: string;
}

interface Entity {
  name: string;
  translation: string;
  type: 'item' | 'monster';
  color: string;
  coords: Coord[];
  quest_npcs?: {
    npc_name: string;
    npc_name_cn: string;
    quest_number: number;
    count: number;
  }[];
  quest_items?: string[];
}

interface GroupData {
  group: string;
  group_display: string;
  entities: Entity[];
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

export default function QuestItemGroupPage() {
  const { group } = useParams<{ group: string }>();
  const dataKey = `quest_items_groups/${group || ''}`;
  const ssrData = useSSRData<GroupData>(dataKey);
  const hasFullData = !!ssrData?.entities?.length;
  const [data, setData] = useState<GroupData | null>(
    hasFullData ? ssrData : null
  );
  const [loading, setLoading] = useState(!hasFullData);
  const { modules } = useDungeonModules();
  const [hidden, setHidden] = useState<Set<string>>(() => {
    if (ssrData?.entities) {
      return new Set(ssrData.entities.map((e) => e.name));
    }
    return new Set();
  });
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set());
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();
  const { tokens, dark } = useTheme();
  const ctrlBtn = useCtrlBtn();
  const ctrlInput = useCtrlInput();

  useEffect(() => {
    if (!group) return;
    if (ssrData?.entities?.length) {
      setLoading(false);
      return;
    }
    fetch(`/data/json/quest_items_groups/${encodeURIComponent(group)}.json`)
      .then<GroupData>((r) => r.json())
      .then((gd) => {
        setData(gd);
        setHidden(new Set(gd.entities.map((e) => e.name)));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [group, ssrData]);

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        加载中...
      </div>
    );
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

  const toggle = (entityName: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(entityName)) next.delete(entityName);
      else next.add(entityName);
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

  const entities = data.entities ?? [];

  const mapGroups = new Map<
    string,
    {
      mod: DungeonModule | undefined;
      dots: {
        entity: Entity;
        x: number;
        y: number;
        z: number;
        file: string;
        idx: number;
      }[];
    }
  >();
  for (const e of entities) {
    e.coords.forEach((c, j) => {
      if (hidden.has(e.name) || hiddenRows.has(`${e.name}-${j}`)) return;
      if (!mapGroups.has(c.map))
        mapGroups.set(c.map, { mod: modules.get(c.map), dots: [] });
      mapGroups
        .get(c.map)!
        .dots.push({ entity: e, x: c.x, y: c.y, z: c.z, file: c.file, idx: j });
    });
  }

  const items = [...mapGroups.entries()].map(([mapName, { mod, dots }]) => ({
    mapName,
    mod,
    dots,
  }));

  const groupedByType = new Map<string, typeof items>();
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
      return groupOrder.indexOf(a) - groupOrder.indexOf(b);
    }
  );

  const totalCoords = [...mapGroups.values()].reduce(
    (s, mg) => s + mg.dots.length,
    0
  );
  const visibleCount = entities.filter((e) => !hidden.has(e.name)).length;

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
          {data.group_display} 任务物品 | 越来越黑暗闪电指南 DarkFlashNav
        </title>
        <meta
          name="description"
          content={`${data.group_display} 任务物品位置，${visibleCount} 个实体，${totalCoords} 个位置点。`}
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
        【{data.group_display}】任务物品
        <span style={{ color: tokens.muted, fontSize: 14, marginLeft: 12 }}>
          {entities.length}种实体 {totalCoords}个位置
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
            if (hidden.size === 0) {
              setHidden(new Set(entities.map((e) => e.name)));
            } else {
              setHidden(new Set());
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
        {entities.map((e) => (
          <button
            key={e.name}
            onClick={() => toggle(e.name)}
            style={{
              padding: '8px 15px',
              border: `2px solid ${e.color}`,
              borderRadius: 5,
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 'bold',
              color: tokens.text,
              background: hidden.has(e.name) ? 'transparent' : e.color,
              opacity: hidden.has(e.name) ? 0.3 : 1,
              transition: 'all 0.2s',
            }}
          >
            {e.type === 'item' ? '📦' : '👹'} {e.translation} ({e.coords.length}
            )
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
          <strong style={{ color: tokens.text }}>实体图例：</strong>
          {entities.map((e) => (
            <span
              key={e.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                cursor: 'pointer',
                opacity: hidden.has(e.name) ? 0.3 : 1,
              }}
              onClick={() => toggle(e.name)}
            >
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: e.color,
                }}
              ></span>
              {e.translation}{' '}
              <span style={{ color: tokens.muted }}>({e.coords.length})</span>
            </span>
          ))}
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
                  fontSize: 22,
                  fontWeight: 'bold',
                  color: dark ? '#FFC107' : '#F57F17',
                  padding: '5px 0',
                  marginTop: 10,
                  borderBottom: dark
                    ? '2px solid #FFC107'
                    : '2px solid #F57F17',
                }}
              >
                {GROUP_LABELS[groupName] || groupName}
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
                  <MapPanel
                    imgName={
                      mod?.img_name || mod?.sl_base_name || 'RareModule_1x1'
                    }
                    sx={sx}
                    sy={sy}
                    dots={dots.map((d) => ({
                      x: d.x,
                      y: d.y,
                      z: d.z,
                      color: d.entity.color,
                      title: d.entity.translation,
                    }))}
                    offX={offX}
                    offY={offY}
                    adj={adj}
                    range={range}
                  />
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
                    {[...new Set(dots.map((d) => d.entity.name))].map((en) => {
                      const e = entities.find((x) => x.name === en)!;
                      return (
                        <span
                          key={en}
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
                              background: e.color,
                              flexShrink: 0,
                            }}
                          ></span>
                          <span
                            style={{ cursor: 'pointer' }}
                            onClick={() => toggle(en)}
                          >
                            {e.translation}
                          </span>
                          <span style={{ color: tokens.muted }}>
                            ({dots.filter((d) => d.entity.name === en).length}
                            点)
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
          const rows = entities.flatMap((e) =>
            e.coords.map((c, j) => {
              const mod = modules.get(c.map);
              const g = mod?.group || '';
              const rowKey = `${e.name}-${j}`;
              return {
                key: rowKey,
                group: GROUP_LABELS[g] || g,
                monster: {
                  name: e.name,
                  translation: e.translation,
                  color: e.color,
                  onToggle: () => toggle(e.name),
                },
                file: c.file,
                mapName: c.map,
                mapLabel: mod?.translation || c.map,
                label: c.label || '',
                x: c.x,
                y: c.y,
                z: c.z,
                hidden: hidden.has(e.name) || hiddenRows.has(rowKey),
              };
            })
          );
          function batchToggle(pred: (r: (typeof rows)[number]) => boolean) {
            const matched = rows.filter(pred);
            if (matched.length === 0) return;
            const allHidden = matched.every((r) => r.hidden);
            for (const r of matched) {
              const eName = r.monster?.name;
              if (allHidden) {
                if (eName && hidden.has(eName)) {
                  toggle(eName);
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
