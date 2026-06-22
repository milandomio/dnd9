import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useDataVersion } from '../hooks/useDataVersion';
import { useDebug } from '../hooks/useDebug';
import { useTheme } from '../hooks/useTheme';
import { useDungeonModules } from '../hooks/useDungeonModules';
import {
  getAdj,
  useCtrlBtn,
  useCtrlInput,
  type AdjState,
} from '../components/MapDebug';
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

interface CoordEntity {
  name: string;
  translation?: string;
  type: string;
  color: string;
  mutually_exclusive?: boolean;
  group_size?: number;
  coords: { x: number; y: number; z: number; version: string; label: string }[];
}

interface ModuleCoordsData {
  map_base: string;
  entities: CoordEntity[];
}

export default function DungeonModuleDetailPage() {
  const { group, name } = useParams<{ group: string; name: string }>();
  const { modules } = useDungeonModules();
  const [coordsData, setCoordsData] = useState<ModuleCoordsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set());
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();
  const { tokens, dark } = useTheme();
  const ctrlBtn = useCtrlBtn();
  const ctrlInput = useCtrlInput();

  const dataVersion = useDataVersion();

  const mod = (name && modules.get(name)) || null;

  useEffect(() => {
    if (!group || !name || !dataVersion) return;
    fetch(
      `/data/json/dungeon_modules_coords/${encodeURIComponent(name)}.json?v=${dataVersion}`
    )
      .then<ModuleCoordsData>((r) => r.json())
      .then((coords) => {
        setCoordsData(coords);
        if (coords) {
          setHidden(new Set(coords.entities.map((e) => e.name)));
        }
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [group, name, dataVersion]);

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        加载中...
      </div>
    );
  if (!mod)
    return (
      <div style={{ textAlign: 'center', color: '#ff6b6b', marginTop: 100 }}>
        数据加载中...
      </div>
    );

  const m = mod;
  const groupLabel = GROUP_LABELS[m.group] || m.group || '未分组';
  const sx = m.size_x || 1;
  const sy = m.size_y || 1;
  const baseRange = m.range || Math.max(sx, sy) * 1600 || 1600;
  const adj = getAdj(m.name, m.rotate, adjOffsets);
  const range = baseRange + adj.range || 1600;
  const offX = (m.offset_x || 0) + adj.x;
  const offY = (m.offset_y || 0) + adj.y;

  function setAdjField(field: string, value: number | boolean) {
    setAdjOffsets((prev: AdjState) => {
      const cur = prev[m.name] || {
        x: 0,
        y: 0,
        range: 0,
        rotate: 0,
        mirrorX: false,
        mirrorY: false,
      };
      return { ...prev, [m.name]: { ...cur, [field]: value } };
    });
  }

  const entities = coordsData?.entities ?? [];
  const totalCoords = entities.reduce(
    (s, e) => s + (hidden.has(e.name) ? 0 : e.coords.length),
    0
  );

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

  const dots: {
    entity: CoordEntity;
    x: number;
    y: number;
    z: number;
    idx: number;
  }[] = [];
  for (const e of entities) {
    e.coords.forEach((c, j) => {
      if (hidden.has(e.name) || hiddenRows.has(`${e.name}-${j}`)) return;
      dots.push({ entity: e, x: c.x, y: c.y, z: c.z, idx: j });
    });
  }

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
        <title>{m.translation} 地图模块 | DarkFindV5游戏导航</title>
        <meta
          name="description"
          content={`${m.translation} 地图模块详情，${sx}x${sy}，分组 ${groupLabel}，${entities.length} 个实体，${totalCoords} 个位置。`}
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
        【{m.translation}】地图模块
        <span style={{ color: tokens.muted, fontSize: 14, marginLeft: 12 }}>
          {groupLabel} | {sx}x{sy}
        </span>
      </h1>

      <div
        style={{
          display: 'grid',
          gap: 6,
          gridTemplateColumns: 'repeat(8, 1fr)',
        }}
      >
        <div
          key={m.name}
          style={{
            gridColumn: entities.length > 0 ? 'span 5' : 'span 8',
            background: tokens.surface,
            border: `1px solid ${tokens.border}`,
            borderRadius: 5,
            padding: 8,
          }}
        >
          <MapPanel
            imgName={m.img_name || m.sl_base_name || 'RareModule_1x1'}
            sx={sx}
            sy={sy}
            dots={dots.map((d) => ({
              x: d.x,
              y: d.y,
              z: d.z,
              color: d.entity.color,
              title: d.entity.translation || d.entity.name,
            }))}
            offX={offX}
            offY={offY}
            adj={adj}
            range={range}
          />
        </div>

        {entities.length > 0 && (
          <div
            style={{
              gridColumn: 'span 3',
              background: tokens.surface,
              border: `1px solid ${tokens.border}`,
              borderRadius: 5,
              padding: 8,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
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
                padding: '8px 0',
                border: `2px solid ${tokens.border}`,
                borderRadius: 5,
                cursor: 'pointer',
                fontSize: 22,
                fontWeight: 'bold',
                color: tokens.text,
                background: 'transparent',
                transition: 'all 0.2s',
                width: '100%',
              }}
            >
              {hidden.size === 0 ? '隐藏全部' : '全部显示'}
            </button>
            {(['monster', 'item', 'props', 'decoration'] as const).map(
              (type) => {
                const group = entities.filter((e) => e.type === type);
                if (!group.length) return null;
                const labels: Record<string, { icon: string; label: string }> =
                  {
                    monster: { icon: '👹', label: '怪物' },
                    item: { icon: '📦', label: '物品' },
                    decoration: { icon: '🔥', label: '装饰' },
                    props: { icon: '🏛️', label: '实体' },
                  };
                const { icon, label } = labels[type];
                return (
                  <div key={type}>
                    <div
                      style={{
                        fontSize: 20,
                        fontWeight: 'bold',
                        color: dark ? '#FFC107' : '#F57F17',
                        marginBottom: 4,
                        paddingLeft: 2,
                      }}
                    >
                      {icon} {label}
                    </div>
                    <div>
                      {group.map((e) => (
                        <button
                          key={e.name}
                          onClick={() => toggle(e.name)}
                          style={{
                            padding: '4px 8px',
                            border: `2px solid ${e.color}`,
                            borderRadius: 5,
                            cursor: 'pointer',
                            fontSize: 19,
                            fontWeight: 'bold',
                            color: tokens.text,
                            background: hidden.has(e.name)
                              ? 'transparent'
                              : e.color,
                            opacity: hidden.has(e.name) ? 0.3 : 1,
                            transition: 'all 0.2s',
                            margin: 2,
                            display: 'inline-flex',
                            alignItems: 'center',
                          }}
                        >
                          {e.translation || e.name}
                          <span style={{ fontSize: 14, marginLeft: 4 }}>
                            ({e.coords.length}
                            {e.mutually_exclusive ? '选1' : '点'})
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              }
            )}
          </div>
        )}

        {debug && (
          <div
            style={{
              gridColumn: '1 / -1',
              fontSize: 11,
              color: tokens.muted,
              marginBottom: 4,
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
              background: tokens.surface,
              borderRadius: 5,
              padding: 8,
            }}
          >
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ color: tokens.muted }}>范围:</span>
              <button
                onClick={() =>
                  setAdjField('range', Math.round(range / 2) - baseRange)
                }
                style={ctrlBtn}
              >
                ÷2
              </button>
              <input
                type="number"
                value={range}
                onChange={(e) =>
                  setAdjField('range', Number(e.target.value) - baseRange)
                }
                style={ctrlInput}
                step={100}
              />
              <button
                onClick={() => setAdjField('range', range * 2 - baseRange)}
                style={ctrlBtn}
              >
                x2
              </button>
              <span
                style={{ color: tokens.muted, fontSize: 12, marginLeft: 4 }}
              >
                ↻{adj.rotate}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ color: tokens.muted }}>偏移:</span>
              <button
                onClick={() => setAdjField('y', adj.y - 50)}
                style={ctrlBtn}
              >
                ↑
              </button>
              <button
                onClick={() => setAdjField('y', adj.y + 50)}
                style={ctrlBtn}
              >
                ↓
              </button>
              <button
                onClick={() => setAdjField('x', adj.x - 50)}
                style={ctrlBtn}
              >
                ←
              </button>
              <button
                onClick={() => setAdjField('x', adj.x + 50)}
                style={ctrlBtn}
              >
                →
              </button>
              <span style={{ color: tokens.muted, marginLeft: 8 }}>X:</span>
              <input
                type="number"
                value={offX}
                onChange={(e) =>
                  setAdjField('x', Number(e.target.value) - (m.offset_x || 0))
                }
                style={ctrlInput}
                step={10}
              />
              <span style={{ color: tokens.muted }}>Y:</span>
              <input
                type="number"
                value={offY}
                onChange={(e) =>
                  setAdjField('y', Number(e.target.value) - (m.offset_y || 0))
                }
                style={ctrlInput}
                step={10}
              />
            </div>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <button
                onClick={() =>
                  setAdjField('rotate', ((adj.rotate ?? 0) + 90) % 360)
                }
                style={ctrlBtn}
              >
                ↻ 旋转
              </button>
              <button
                onClick={() => setAdjField('mirrorX', !adj.mirrorX)}
                style={{
                  ...ctrlBtn,
                  background: adj.mirrorX ? '#4CAF50' : '#555',
                }}
              >
                ⇄ 左右
              </button>
              <button
                onClick={() => setAdjField('mirrorY', !adj.mirrorY)}
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
                    delete n[m.name];
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

      {debug &&
        (() => {
          const rows = entities.flatMap((e) =>
            e.coords.map((c, j) => {
              const rowKey = `${e.name}-${j}`;
              return {
                key: rowKey,
                group: groupLabel,
                monster: {
                  name: e.name,
                  translation: e.name,
                  color: e.color,
                  onToggle: () => toggle(e.name),
                },
                file: '',
                mapName: m.name,
                mapLabel: m.translation || m.name,
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
        {entities.length > 0 && (
          <>
            <br />
            <strong>包含实体：</strong>{' '}
            {entities
              .map((e) => `${e.translation || e.name}(${e.coords.length})`)
              .join('、')}
          </>
        )}
      </div>
    </div>
  );
}
