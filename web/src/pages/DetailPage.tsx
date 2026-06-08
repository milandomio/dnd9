import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { Spin, Typography, Tag } from "antd";
import type { ItemEntity, MonsterEntity, PropsEntity, Coord, DungeonModule } from "../types/data";

const GROUP_LABELS: Record<string, string> = {
  Crypt: "废墟2层地牢",
  FireDeep: "哥布林洞穴2层",
  GoblinCave: "哥布林洞穴1层",
  IceAbyss: "冰图2层",
  IceCavern: "冰图1层",
  Inferno: "废墟3层炼狱",
  Ruins: "废墟1层",
  ShipGraveyard: "水图",
};

type Entity = ItemEntity | MonsterEntity | PropsEntity;

function zColor(z: number): string {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff3333";
}

const GLOW = "0 0 4px #fff, 0 0 2px #000";

const ctrlBtn: CSSProperties = { background: "#555", color: "#ccc", border: "1px solid #777", borderRadius: 3, padding: "1px 6px", cursor: "pointer", fontSize: 11 };
const ctrlInput: CSSProperties = { width: 55, background: "#333", color: "#fff", border: "1px solid #666", borderRadius: 3, padding: "1px 4px", fontSize: 11, textAlign: "center" };

export default function DetailPage() {
  const { page, name } = useParams<{ page: string; name: string }>();
  const [entity, setEntity] = useState<Entity | null>(null);
  const [modules, setModules] = useState<Map<string, DungeonModule>>(new Map());
  const [loading, setLoading] = useState(true);

  const [debug, setDebug] = useState(false);
  const [adjOffsets, setAdjOffsets] = useState<Record<string, {x: number; y: number; range: number; rotate: number; mirrorX: boolean; mirrorY: boolean}>>({});

  function getAdj(mapName: string, mod: DungeonModule | undefined) {
    const a = adjOffsets[mapName];
    return {x: a?.x ?? 0, y: a?.y ?? 0, range: a?.range ?? 0, rotate: a?.rotate ?? mod?.rotate ?? 1, mirrorX: a?.mirrorX ?? false, mirrorY: a?.mirrorY ?? false};
  }

  function setAdj(mapName: string, field: string, value: number | boolean) {
    setAdjOffsets(prev => {
      const cur = prev[mapName] || {x: 0, y: 0, range: 0, rotate: 0, mirrorX: false, mirrorY: false};
      return {...prev, [mapName]: {...cur, [field]: value}};
    });
  }

  useEffect(() => {
    if (!page || !name) return;
    const decoded = decodeURIComponent(name!);
    Promise.all([
      fetch(`./data/${page}/${decoded}.json`).then<Entity>((r) => r.json()),
      fetch(`./data/dungeon_modules.json`).then<DungeonModule[]>((r) => r.json()),
    ])
      .then(([entity, mods]) => {
        setEntity(entity);
        setModules(new Map(mods.map((m) => [m.sl_base_name, m])));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, name]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!entity) return <Typography.Text type="danger">未找到</Typography.Text>;

  const coords = entity.coords;
  const grouped = new Map<string, Coord[]>();
  for (const c of coords) {
    if (!grouped.has(c.map)) grouped.set(c.map, []);
    grouped.get(c.map)!.push(c);
  }

  const groupedByType = new Map<string, Array<{mapName: string; mod: DungeonModule | undefined; coords: Coord[]}>>();
  for (const [mapName, mapCoords] of grouped) {
    const mod = modules.get(mapName);
    const g = mod?.group || "";
    if (!groupedByType.has(g)) groupedByType.set(g, []);
    groupedByType.get(g)!.push({mapName, mod, coords: mapCoords});
  }

  // Sort items within each group by size_x, size_y
  for (const [_, items] of groupedByType) {
    items.sort((a, b) => {
      const sy_a = a.mod?.size_y ?? 1;
      const sy_b = b.mod?.size_y ?? 1;
      const sx_a = a.mod?.size_x ?? 1;
      const sx_b = b.mod?.size_x ?? 1;
      return sy_a - sy_b || sx_a - sx_b;
    });
  }

  const groupOrder = Object.keys(GROUP_LABELS);
  const sortedGroups = [...groupedByType.entries()].sort(([a], [b]) => {
    return groupOrder.indexOf(a) - groupOrder.indexOf(b);
  });

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, margin: "0 0 12px" }}>
        {entity.translation || entity.name} 位置汇总
      </h1>
      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <Typography.Text code style={{ fontSize: 14 }}>
          {entity.name}
        </Typography.Text>
        <button onClick={() => setDebug(!debug)} style={{
          marginLeft: 16, padding: "4px 16px",
          background: debug ? "#4CAF50" : "#FFC107", color: debug ? "#fff" : "#000",
          border: debug ? "2px solid #388E3C" : "2px solid #FF9800",
          borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: "bold",
        }}>
          {debug ? "退出调试" : "显示调试信息"}
        </button>
      </div>

      {"monsters" in entity && entity.monsters && entity.monsters.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Typography.Text strong>掉落来源：</Typography.Text>
          {entity.monsters.map((m) => (
            <Tag key={m} style={{ marginTop: 4 }}>{m}</Tag>
          ))}
        </div>
      )}

      <Typography.Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        共 {coords.length} 个坐标，分布在 {grouped.size} 个模块
      </Typography.Text>

      <div style={{
        textAlign: "center", color: "#ff6b6b", fontSize: 14, marginBottom: 20,
        padding: 8, background: "#3a3a3a", borderRadius: 5, maxWidth: 700, marginLeft: "auto", marginRight: "auto",
      }}>⚠️ 数据有误差，以实际游戏内为准</div>

      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(4, 1fr)" }}>
        {sortedGroups.map(([groupName, items]) => (<>
          {groupName && <div key={`h-${groupName}`} style={{
            gridColumn: "1 / -1",
            fontSize: 22,
            fontWeight: "bold",
            color: "#FFC107",
            padding: "5px 0",
            marginTop: 8,
          }}>{GROUP_LABELS[groupName] || groupName}</div>}
          {items.map(({mapName, mod, coords: mapCoords}) => {
          const sx = mod?.size_x ?? 1;
          const sy = mod?.size_y ?? 1;
          const baseRange = mod?.range || Math.max(sx, sy) * 1600;
          const adj = getAdj(mapName, mod);
          const range = (baseRange + adj.range) || 1600;
          const offX = (mod?.offset_x ?? 0) + adj.x;
          const offY = (mod?.offset_y ?? 0) + adj.y;
          return (
            <div key={mapName} style={{
              minWidth: 0,
              gridColumn: sx >= 2 ? `span ${sx}` : undefined,
              gridRow: sy >= 2 ? `span ${sy}` : undefined,
              background: "#3a3a3a",
              border: "1px solid #555",
              borderRadius: 5,
              padding: 8,
            }}>
              <h3 style={{
                margin: "0 0 6px 0",
                fontSize: 22,
                color: "#00bcd4",
                textAlign: "center",
                width: "100%",
                lineHeight: 1.3,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}>
                {mod?.translation || mapName}
                {debug && <span style={{ color: "#888", fontSize: 11 }}> ({mapName})</span>}
              </h3>
              <div style={{ fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4 }}>
                {mod?.sl_base_name || mapName}.webp | 找到 {mapCoords.length} 个位置 | 范围: ±{range}
              </div>
              {debug && <div style={{ fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4, lineHeight: 1.4 }}>
                {mapCoords[0].file}<br/>
                旋转:{mod?.rotate ?? 0} 偏移:({mod?.offset_x ?? 0},{mod?.offset_y ?? 0}) 大小:{sx}x{sy}
              </div>}

              <div style={{
                aspectRatio: `${sx} / ${sy}`,
                background: "#2c2c2c",
                border: "1px solid #666",
                borderRadius: 4,
                position: "relative",
                overflow: "hidden",
                ...(mod?.sl_base_name ? {
                  backgroundImage: `url(./data/img/${mod.sl_base_name}.webp)`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                } : {}),
              }}>
                {mapCoords.map((c, i) => {
                  let x = c.x + offX;
                  let y = c.y + offY;
                  const r = adj.rotate;
                  if (r === 1) { const nx = y; const ny = -x; x = nx; y = ny; }
                  else if (r === 2) { x = -x; y = -y; }
                  else if (r === 3) { const nx = -y; const ny = x; x = nx; y = ny; }
                  if (adj.mirrorX) x = -x;
                  if (adj.mirrorY) y = -y;
                  const multX = sx === 1 && sy === 2 ? 100 : 50;
                  const centerX = sx === 1 && sy === 2 ? 100 : 50;
                  const multY = 50;
                  const centerY = 50;
                  const px = centerX + (x / range) * multX;
                  const py = centerY + (y / range) * multY;
                  const col = zColor(c.z);
                  const textCol = col === "#ff3333" ? "#ffffff" : col;
                  const textShadow = col === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW;
                   return (
                    <div key={i} style={{
                      position: "absolute",
                      left: `${px}%`,
                      top: `${py}%`,
                      width: 9,
                      height: 9,
                      borderRadius: "50%",
                      background: col,
                      boxShadow: `0 0 6px ${col}`,
                      border: "1px solid #fff",
                      transform: "translate(-50%, -50%)",
                      zIndex: 10,
                    }}>
                      <span style={{
                        position: "absolute",
                        left: "50%",
                        top: "100%",
                        transform: "translateX(-50%)",
                        fontSize: 11,
                        fontFamily: "Arial, sans-serif",
                        color: textCol,
                        whiteSpace: "nowrap",
                        textShadow: textShadow,
                        lineHeight: 1,
                        marginTop: 1,
                      }}>
                        {Math.round(c.z)}
                      </span>
                    </div>
                  );
                })}
              </div>
              {debug && (
              <div style={{ fontSize: 11, color: "#aaa", marginTop: 4, display: "flex", gap: 4, alignItems: "center", flexWrap: "nowrap" }}>
                <span style={{ color: "#888" }}>范围:</span>
                <button onClick={() => setAdj(mapName, "range", Math.round(range / 2) - baseRange)} style={ctrlBtn}>÷2</button>
                <input type="number" value={range} onChange={e => setAdj(mapName, "range", Number(e.target.value) - baseRange)} style={ctrlInput} step={100} />
                <button onClick={() => setAdj(mapName, "range", range * 2 - baseRange)} style={ctrlBtn}>x2</button>
                <span style={{ color: "#aaa", fontSize: 12, marginLeft: 4 }}>↻{adj.rotate}</span>
                <span style={{ color: "#888", marginLeft: 8 }}>偏移:</span>
                <button onClick={() => setAdj(mapName, "y", adj.y - 50)} style={ctrlBtn}>↑</button>
                <button onClick={() => setAdj(mapName, "y", adj.y + 50)} style={ctrlBtn}>↓</button>
                <button onClick={() => setAdj(mapName, "x", adj.x - 50)} style={ctrlBtn}>←</button>
                <button onClick={() => setAdj(mapName, "x", adj.x + 50)} style={ctrlBtn}>→</button>
                <span style={{ color: "#888", marginLeft: 8 }}>X:</span>
                <input type="number" value={offX} onChange={e => setAdj(mapName, "x", Number(e.target.value) - (mod?.offset_x ?? 0))} style={ctrlInput} step={10} />
                <span style={{ color: "#888" }}>Y:</span>
                <input type="number" value={offY} onChange={e => setAdj(mapName, "y", Number(e.target.value) - (mod?.offset_y ?? 0))} style={ctrlInput} step={10} />
                <button onClick={() => setAdj(mapName, "rotate", (adj.rotate + 1) % 4)} style={ctrlBtn}>↻ 旋转</button>
                <button onClick={() => setAdj(mapName, "mirrorX", !adj.mirrorX)} style={{...ctrlBtn, background: adj.mirrorX ? "#4CAF50" : "#555"}}>⇄ 左右</button>
                <button onClick={() => setAdj(mapName, "mirrorY", !adj.mirrorY)} style={{...ctrlBtn, background: adj.mirrorY ? "#4CAF50" : "#555"}}>⇅ 上下</button>
                <button onClick={() => setAdjOffsets(prev => { const n = {...prev}; delete n[mapName]; return n; })} style={ctrlBtn}>↺ 重置</button>
              </div>
              )}
            </div>
          );
          })}
        </>))}
      </div>

      <div style={{ marginTop: 24, display: "flex", justifyContent: "center", gap: 24, fontSize: 12, color: "#aaa" }}>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#00ffff", marginRight: 4 }}></span> Z &gt; 299 (高于地面)</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#ffff00", marginRight: 4 }}></span> -299 ≤ Z ≤ 299 (正常高度)</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#ff4444", marginRight: 4 }}></span> Z &lt; -299 (低于地面)</span>
      </div>
    </div>
  );
}
