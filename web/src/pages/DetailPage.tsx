import { useEffect, useRef, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Typography } from 'antd';
import type {
  ItemEntity,
  MonsterEntity,
  PropsEntity,
  Coord,
  DungeonModule,
  GroupDropInfo,
} from '../types/data';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useDebug } from '../hooks/useDebug';
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
  const [entity, setEntity] = useState<Entity | null>(
    ssrData?.entity?._modules ? ssrData.entity : null
  );
  const dataVersion = useDataVersion();

  // Build local modules map from entity's inline _modules data
  const modules = useMemo(() => {
    if (!entity?._modules) return new Map<string, DungeonModule>();
    const mm = new Map<string, DungeonModule>();
    for (const [mapName, data] of Object.entries(entity._modules)) {
      const mod: DungeonModule = {
        name: mapName,
        names: [mapName],
        translation: data.translation,
        group: data.group,
        size_x: data.size_x,
        size_y: data.size_y,
        sl_base_name: data.sl_base_name,
        img_name: data.img_name,
        has_img: true,
        has_useful_entities: true,
        offset_x: data.offset_x,
        offset_y: data.offset_y,
        rotate: data.rotate,
        range: data.range,
      };
      mm.set(mapName, mod);
    }
    return mm;
  }, [entity?._modules]);
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set());
  const fetchedRef = useRef(false);

  // Reset fetch guard when navigating between entities
  useEffect(() => {
    fetchedRef.current = false;
  }, [page, name]);

  const { debug, toggle, adjOffsets, setAdjOffsets } = useDebug();
  const { tokens, dark } = useTheme();
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
    if (ssrData?.entity?.coords) {
      setEntity(ssrData.entity);
      return;
    }
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    const decoded = decodeURIComponent(name!);
    const url = dataVersion
      ? `/data/json/${page}/${decoded}.json?v=${dataVersion}`
      : `/data/json/${page}/${decoded}.json`;
    fetch(url)
      .then<Entity>((r) => r.json())
      .then((entityData) => {
        setEntity(entityData);
      })
      .catch(console.error);
  }, [page, name, ssrData, dataVersion]);

  if (!entity)
    return <Typography.Text type="danger">数据加载中...</Typography.Text>;

  const coords = entity.coords ?? [];
  const visibleCoords = coords.filter(
    (c, i) => !hiddenRows.has(`${c.file}-${i}`)
  );
  const grouped = new Map<string, Coord[]>();
  for (const c of visibleCoords) {
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
          {entity.translation || entity.name} 位置汇总 | 越来越黑暗光速指南
          DarkFlashNav
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
          color: tokens.accent,
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
                  {(() => {
                    const gdi = entity.group_drop_info?.[groupName] as
                      | GroupDropInfo[]
                      | undefined;
                    if (!gdi || gdi.length === 0) return null;
                    // Collect all coord labels across the group
                    const allLabels = items.flatMap((it) =>
                      it.coords.map((c) => c.label || '')
                    );
                    const hasType = (t: string) =>
                      allLabels.some((l) => l.includes(t));
                    const hasUndersea = hasType('海底');
                    const hasSpecial = hasType('特殊') || hasType('华丽');
                    const hasRandom = hasType('随机') || hasType('Random');
                    const hasRegular = allLabels.some(
                      (l) =>
                        l &&
                        !l.includes('海底') &&
                        !l.includes('特殊') &&
                        !l.includes('华丽') &&
                        !l.includes('随机') &&
                        !l.includes('Random')
                    );
                    const filtered = gdi.filter((info) => {
                      const t = info.translation;
                      const isUndersea = t.includes('海底');
                      const isSpecial = t.includes('特殊');
                      const isRandom = t.includes('随机');
                      if (isUndersea && !hasUndersea) return false;
                      if (isSpecial && !hasSpecial) return false;
                      if (isRandom && !hasRandom) return false;
                      if (!isUndersea && !isSpecial && !isRandom && !hasRegular)
                        return false;
                      return true;
                    });
                    if (filtered.length === 0) return null;
                    return (
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 'normal',
                          color: tokens.muted,
                        }}
                      >
                        参考爆率：
                        {filtered.map((info, gi) => (
                          <span
                            key={gi}
                            style={{
                              display: 'inline-block',
                              marginRight: 8,
                            }}
                          >
                            {info.translation}
                            {info.spawn_rate}%
                            {Object.entries(info.drop_rates)
                              .map(([mode, rate]) => `[${mode}:${rate}%]`)
                              .join('')}
                          </span>
                        ))}
                      </span>
                    );
                  })()}
                </div>
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
              if (mapCoords.length === 0) return null;
              const filteredDots = mapCoords.map((c) => ({
                x: c.x,
                y: c.y,
                z: c.z,
                color: '',
              }));
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
                  {(() => {
                    const g = mod?.group || '';
                    const gdi = entity.group_drop_info?.[g];
                    if (!gdi || gdi.length === 0) return null;
                    const hasVariant = mapCoords.some(
                      (c) => c.variant_count && c.variant_count > 1
                    );
                    if (!hasVariant) return null;
                    // Collect spawner types present in this module's coords
                    const labels = mapCoords.map((c) => c.label || '');
                    const hasType = (t: string) =>
                      labels.some((l) => l.includes(t));
                    const hasUndersea = hasType('海底');
                    const hasSpecial = hasType('特殊') || hasType('华丽');
                    const hasRandom = hasType('随机') || hasType('Random');
                    const hasRegular = labels.some(
                      (l) =>
                        l &&
                        !l.includes('海底') &&
                        !l.includes('特殊') &&
                        !l.includes('华丽') &&
                        !l.includes('随机')
                    );
                    const filteredGdi = gdi.filter((info) => {
                      const t = info.translation;
                      const isUndersea = t.includes('海底');
                      const isSpecial = t.includes('特殊');
                      const isRandom = t.includes('随机');
                      if (isUndersea && !hasUndersea) return false;
                      if (isSpecial && !hasSpecial) return false;
                      if (isRandom && !hasRandom) return false;
                      if (!isUndersea && !isSpecial && !isRandom && !hasRegular)
                        return false;
                      return true;
                    });
                    if (filteredGdi.length === 0) return null;
                    return (
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
                        {filteredGdi.map((info, i) => (
                          <span
                            key={i}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 3,
                            }}
                          >
                            <span
                              style={{
                                cursor: 'default',
                              }}
                            >
                              {info.translation}
                            </span>
                            {info.spawn_rates &&
                            Object.keys(info.spawn_rates).length > 1 ? (
                              <span
                                style={{
                                  color: tokens.muted,
                                  fontSize: 12,
                                }}
                              >
                                {Object.entries(info.drop_rates)
                                  .map(([mode, rate]) => {
                                    const sRate = info.spawn_rates![mode];
                                    return sRate != null
                                      ? `[${mode}:${sRate}%×${rate}%]`
                                      : `[${mode}:${rate}%]`;
                                  })
                                  .join('')}
                              </span>
                            ) : (
                              <>
                                <span
                                  style={{
                                    color: tokens.accent,
                                    fontSize: 12,
                                  }}
                                >
                                  {info.spawn_rate}%
                                </span>
                                {Object.keys(info.drop_rates).length > 0 && (
                                  <span
                                    style={{
                                      color: tokens.muted,
                                      fontSize: 12,
                                    }}
                                  >
                                    (
                                    {Object.entries(info.drop_rates)
                                      .map(
                                        ([mode, rate]) => `[${mode}:${rate}%]`
                                      )
                                      .join('')}
                                    )
                                  </span>
                                )}
                              </>
                            )}
                          </span>
                        ))}
                        {(() => {
                          const vc = mapCoords.find(
                            (c) => c.variant_count && c.variant_count > 1
                          );
                          if (!vc) return null;
                          const names = vc.variant_names ?? [];
                          if (names.length > 0) {
                            return (
                              <span style={{ color: tokens.muted }}>
                                ({names.join('、')}
                                {vc.variant_count}种选1)
                              </span>
                            );
                          }
                          const uniquePositions = new Set(
                            mapCoords.map((c) => `${c.x},${c.y},${c.z}`)
                          );
                          return (
                            <span style={{ color: tokens.muted }}>
                              ({uniquePositions.size}点选1)
                            </span>
                          );
                        })()}
                      </div>
                    );
                  })()}
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
        <strong>位置统计：共 {visibleCoords.length} 个位置点</strong>
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
                color: tokens.accent,
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
            for (const r of matched) toggleRow(r.key, allHidden);
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
