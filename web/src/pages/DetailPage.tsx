import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Typography } from 'antd';
import type {
  ItemEntity,
  MonsterEntity,
  PropsEntity,
  Coord,
  DungeonModule,
} from '../types/data';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useDebug } from '../hooks/useDebug';
import { useDungeonModules } from '../hooks/useDungeonModules';
import { useTheme } from '../hooks/useTheme';
import {
  getAdj,
  useCtrlBtn,
  useCtrlInput,
  type AdjState,
} from '../components/MapDebug';
import Disclaimer from '../components/Disclaimer';
import DebugCoordTable from '../components/DebugCoordTable';
import MapPanel from '../components/MapPanel';

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

type Entity = ItemEntity | MonsterEntity | PropsEntity;

export default function DetailPage() {
  const { page, name } = useParams<{ page: string; name: string }>();
  const dataKey = `${page}/${name ? decodeURIComponent(name) : ''}`;
  const ssrData = useSSRData<{ entity: Entity; modules: DungeonModule[] }>(
    dataKey
  );
  const [entity, setEntity] = useState<Entity | null>(ssrData?.entity || null);
  const { modules } = useDungeonModules();
  const dataVersion = useDataVersion();
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set());

  const { debug, toggle, adjOffsets, setAdjOffsets } = useDebug();
  const { tokens } = useTheme();
  const ctrlBtn = useCtrlBtn();
  const ctrlInput = useCtrlInput();

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

  useEffect(() => {
    if (!page || !name) return;
    if (ssrData?.entity?.coords) return;
    const decoded = decodeURIComponent(name!);
    fetch(`./data/json/${page}/${decoded}.json?v=${dataVersion}`)
      .then<Entity>((r) => r.json())
      .then((entityData) => {
        setEntity(entityData);
      })
      .catch(console.error);
  }, [page, name, ssrData]);

  if (!entity)
    return <Typography.Text type="danger">数据加载中...</Typography.Text>;

  const coords = entity.coords ?? [];
  // Build a lookup from coord properties to index for hidden check
  const coordKeyToIndex = new Map<string, number>();
  coords.forEach((c, i) => {
    coordKeyToIndex.set(`${c.file}|${c.x}|${c.y}|${c.z}`, i);
  });
  const grouped = new Map<string, Coord[]>();
  for (const c of coords) {
    if (!grouped.has(c.map)) grouped.set(c.map, []);
    grouped.get(c.map)!.push(c);
  }

  const groupedByType = new Map<
    string,
    Array<{ mapName: string; mod: DungeonModule | undefined; coords: Coord[] }>
  >();
  for (const [mapName, mapCoords] of grouped) {
    const mod = modules.get(mapName);
    const g = mod?.group || '';
    if (!groupedByType.has(g)) groupedByType.set(g, []);
    groupedByType.get(g)!.push({ mapName, mod, coords: mapCoords });
  }

  // Sort items within each group: size first, then coord count
  for (const [, items] of groupedByType) {
    items.sort((a, b) => {
      const sy_a = a.mod?.size_y ?? 1;
      const sy_b = b.mod?.size_y ?? 1;
      const sx_a = a.mod?.size_x ?? 1;
      const sx_b = b.mod?.size_x ?? 1;
      if (sy_a !== sy_b) return sy_a - sy_b;
      if (sx_a !== sx_b) return sx_a - sx_b;
      return b.coords.length - a.coords.length;
    });
  }

  const groupOrder = Object.keys(GROUP_LABELS);
  const sortedGroups = [...groupedByType.entries()].sort(
    ([a, aItems], [b, bItems]) => {
      const totalA = aItems.reduce((s, item) => s + item.coords.length, 0);
      const totalB = bItems.reduce((s, item) => s + item.coords.length, 0);
      if (totalA !== totalB) return totalB - totalA;
      if (!a && !b) return 0;
      if (!a) return 1;
      if (!b) return -1;
      return groupOrder.indexOf(a) - groupOrder.indexOf(b);
    }
  );

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {entity.translation || entity.name} 位置汇总 | DarkFindV5游戏导航
        </title>
        <meta
          name="description"
          content={`${entity.translation || entity.name}（${entity.name}）在游戏内的地图位置分布，共 ${coords.length} 个位置点。`}
        />
        <meta
          property="og:title"
          content={`${entity.translation || entity.name} 位置汇总 | DarkFindV5`}
        />
        <meta
          property="og:description"
          content={`${entity.translation || entity.name} 共 ${coords.length} 个位置点`}
        />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: '#00bcd4',
          fontSize: 36,
          margin: '0 0 12px',
        }}
      >
        {entity.translation || entity.name} 位置汇总
      </h1>

      <button
        onClick={toggle}
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

      <Disclaimer />

      <div
        style={{
          display: 'grid',
          gap: 6,
          gridTemplateColumns: 'repeat(4, 1fr)',
        }}
      >
        {sortedGroups.map(([groupName, items]) => (
          <>
            {groupName && (
              <div
                key={`h-${groupName}`}
                style={{
                  gridColumn: '1 / -1',
                  fontSize: 22,
                  fontWeight: 'bold',
                  color: '#FFC107',
                  padding: '5px 0',
                  marginTop: 10,
                  borderBottom: '2px solid #FFC107',
                }}
              >
                {GROUP_LABELS[groupName] || groupName}
              </div>
            )}
            {items.map(({ mapName, mod, coords: mapCoords }) => {
              const sx = mod?.size_x ?? 1;
              const sy = mod?.size_y ?? 1;
              const baseRange = mod?.range || Math.max(sx, sy) * 1600;
              const adj = myGetAdj(mapName, mod);
              const range = baseRange + adj.range || 1600;
              const offX = (mod?.offset_x ?? 0) + adj.x;
              const offY = (mod?.offset_y ?? 0) + adj.y;
              const filteredDots = mapCoords
                .filter((c) => {
                  const idx = coordKeyToIndex.get(
                    `${c.file}|${c.x}|${c.y}|${c.z}`
                  );
                  return !(
                    idx !== undefined && hiddenRows.has(`${c.file}-${idx}`)
                  );
                })
                .map((c) => ({ x: c.x, y: c.y, z: c.z, color: '' }));
              if (filteredDots.length === 0) return null;
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
                      color: '#00bcd4',
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
                      找到 {mapCoords.length} 个位置 | 范围: ±{range}
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
                      {mapCoords[0].file}
                      <br />
                      旋转:{mod?.rotate ?? 0} 偏移:({mod?.offset_x ?? 0},
                      {mod?.offset_y ?? 0}) 大小:{sx}x{sy}
                    </div>
                  )}

                  <MapPanel
                    imgName={
                      mod?.img_name || mod?.sl_base_name || 'RareModule_1x1'
                    }
                    sx={sx}
                    sy={sy}
                    dots={filteredDots}
                    offX={offX}
                    offY={offY}
                    adj={adj}
                    range={range}
                    singleCategory
                  />
                  {debug && (
                    <div
                      style={{
                        fontSize: 11,
                        color: tokens.muted,
                        marginTop: 4,
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
                </div>
              );
            })}
          </>
        ))}
      </div>

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
        <strong>颜色说明：</strong>
        <span
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#00ffff',
            marginRight: 3,
          }}
        ></span>{' '}
        Z &gt; 299 (高于地面)
        <span
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#ffff00',
            margin: '0 3px 0 12px',
          }}
        ></span>{' '}
        -299 ≤ Z ≤ 299 (正常高度)
        <span
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#ff4444',
            margin: '0 3px 0 12px',
          }}
        ></span>{' '}
        Z &lt; -299 (低于地面)
        <br />
        <strong>位置统计：共 {coords.length} 个位置点</strong>
        <br />
        <strong>包含地图：</strong>{' '}
        {[...grouped.keys()]
          .map((k) => modules.get(k)?.translation || k)
          .join(', ')}
      </div>

      {debug &&
        (() => {
          const rows = coords.map((c, i) => {
            const mod = modules.get(c.map);
            const g = mod?.group || '';
            const rowKey = `${c.file}-${i}`;
            return {
              key: rowKey,
              group: GROUP_LABELS[g] || g,
              groupKey: g,
              monster: {
                name: name || '',
                translation: name || '',
                color: '#00bcd4',
              },
              file: c.file,
              mapName: c.map,
              mapLabel: mod?.translation || c.map,
              label: c.label || '',
              x: c.x,
              y: c.y,
              z: c.z,
              hidden: hiddenRows.has(rowKey),
            };
          });
          function batchToggle(pred: (r: (typeof rows)[number]) => boolean) {
            const matched = rows.filter(pred);
            if (matched.length === 0) return;
            const allHidden = matched.every((r) => r.hidden);
            for (const r of matched) toggleRow(r.key, !allHidden);
          }
          return (
            <DebugCoordTable
              rows={rows}
              onToggleRow={toggleRow}
              onToggleGroup={(gk) => batchToggle((r) => r.groupKey === gk)}
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
    </div>
  );
}
