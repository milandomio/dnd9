import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { useDebug } from "../hooks/useDebug";
import { getAdj, applyTransform, computePixel, ctrlBtn, ctrlInput, type AdjState } from "../components/MapDebug";
import DebugCoordTable from "../components/DebugCoordTable";
import type { DungeonModule } from "../types/data";

const GROUP_LABELS: Record<string, string> = {
  Crypt: "废墟2层地牢",
  FireDeep: "哥布林洞穴2层",
  GoblinCave: "哥布林洞穴1层",
  IceAbyss: "冰图2层",
  IceCavern: "冰图1层",
  Inferno: "废墟3层炼狱",
  Ruins: "废墟1层",
  ShipGraveyard: "水图",
  Swamp: "沼泽",
};

interface CoordEntity {
  name: string;
  type: string;
  color: string;
  coords: { x: number; y: number; z: number; version: string }[];
}

interface ModuleCoordsData {
  map_base: string;
  entities: CoordEntity[];
}

function zColor(z: number): string {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff3333";
}

const GLOW = "0 0 4px #fff, 0 0 2px #000";

export default function DungeonModuleDetailPage() {
  const { group, name } = useParams<{ group: string; name: string }>();
  const [mod, setMod] = useState<DungeonModule | null>(null);
  const [coordsData, setCoordsData] = useState<ModuleCoordsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set());
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();

  useEffect(() => {
    if (!group || !name) return;
    Promise.all([
      fetch("./data/json/dungeon_modules.json")
        .then<DungeonModule[]>((r) => r.json())
        .then((mods) => mods.find((m) => m.name === name && m.group === group) || null),
      fetch(`./data/json/dungeon_modules_coords/${encodeURIComponent(name)}.json`)
        .then<ModuleCoordsData>((r) => r.json())
        .catch(() => null),
    ])
      .then(([foundMod, coords]) => {
        setMod(foundMod);
        setCoordsData(coords);
        if (coords) {
          setHidden(new Set(coords.entities.map(e => e.name)));
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [group, name]);

  if (loading) return <div style={{ textAlign: "center", color: "#aaa", marginTop: 100 }}>加载中...</div>;
  if (!mod) return <div style={{ textAlign: "center", color: "#ff6b6b", marginTop: 100 }}>未找到</div>;

  const m = mod;
  const groupLabel = GROUP_LABELS[m.group] || m.group || "未分组";
  const sx = m.size_x || 1;
  const sy = m.size_y || 1;
  const baseRange = m.range || Math.max(sx, sy) * 1600 || 1600;
  const adj = getAdj(m.name, m.rotate, adjOffsets);
  const range = (baseRange + adj.range) || 1600;
  const offX = (m.offset_x || 0) + adj.x;
  const offY = (m.offset_y || 0) + adj.y;

  function setAdjField(field: string, value: number | boolean) {
    setAdjOffsets((prev: AdjState) => {
      const cur = prev[m.name] || { x: 0, y: 0, range: 0, rotate: 0, mirrorX: false, mirrorY: false };
      return { ...prev, [m.name]: { ...cur, [field]: value } };
    });
  }

  const entities = coordsData?.entities ?? [];
  const totalCoords = entities.reduce((s, e) => s + (hidden.has(e.name) ? 0 : e.coords.length), 0);
  const visibleCount = entities.filter(e => !hidden.has(e.name)).length;

  const toggle = (entityName: string) => {
    setHidden(prev => {
      const next = new Set(prev);
      if (next.has(entityName)) next.delete(entityName);
      else next.add(entityName);
      return next;
    });
  };

  const dots: { entity: CoordEntity; x: number; y: number; z: number }[] = [];
  for (const e of entities) {
    if (hidden.has(e.name)) continue;
    for (const c of e.coords) {
      dots.push({ entity: e, x: c.x, y: c.y, z: c.z });
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <button onClick={toggleDebug} style={{
        position: "fixed", top: 20, right: 20,
        padding: "4px 16px",
        background: debug ? "#4CAF50" : "#FFC107",
        color: debug ? "#fff" : "#000",
        border: debug ? "2px solid #388E3C" : "2px solid #FF9800",
        borderRadius: 6, cursor: "pointer", fontSize: 13,
        fontWeight: "bold", zIndex: 9999,
        boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
      }}>
        {debug ? "退出调试" : "显示调试信息"}
      </button>

      <Helmet>
        <title>{m.translation} 地图模块 | DarkFindV5游戏导航</title>
        <meta name="description" content="{m.translation} 地图模块详情，{sx}x{sy}，分组 {groupLabel}，{visibleCount} 个实体，{totalCoords} 个位置。" />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 28, margin: "0 0 8px" }}>
        【{m.translation}】地图模块
        <span style={{ color: "#aaa", fontSize: 14, marginLeft: 12 }}>{groupLabel} | {sx}x{sy} | 旋转:{m.rotate}</span>
      </h1>

      {entities.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", margin: "15px 0", padding: 10, background: "#3a3a3a", borderRadius: 5 }}>
          <button onClick={() => {
            if (hidden.size === 0) {
              setHidden(new Set(entities.map(e => e.name)));
            } else {
              setHidden(new Set());
            }
          }} style={{
            padding: "8px 15px", border: "2px solid #888", borderRadius: 5,
            cursor: "pointer", fontSize: 14, fontWeight: "bold", color: "#ccc",
            background: "transparent", transition: "all 0.2s",
          }}>
            {hidden.size === 0 ? "隐藏全部" : "全部显示"}
          </button>
          {entities.map(e => (
            <button key={e.name} onClick={() => toggle(e.name)} style={{
              padding: "8px 15px", border: `2px solid ${e.color}`, borderRadius: 5,
              cursor: "pointer", fontSize: 14, fontWeight: "bold", color: "#fff",
              background: hidden.has(e.name) ? "transparent" : e.color,
              opacity: hidden.has(e.name) ? 0.3 : 1,
              transition: "all 0.2s",
            }}>
              {e.type === "item" ? "📦" : e.type === "props" ? "🏛️" : "👹"} {e.name} ({e.coords.length})
            </button>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gap: 6, gridTemplateColumns: "repeat(4, 1fr)" }}>
        <div key={m.name} style={{
          gridColumn: "1 / -1", background: "#3a3a3a", border: "1px solid #555",
          borderRadius: 5, padding: 8,
        }}>
          <h3 style={{ margin: "0 0 6px 0", fontSize: 22, color: "#00bcd4", textAlign: "center", width: "100%" }}>
            {m.translation || m.name}
            {debug && <span style={{ color: "#888", fontSize: 11 }}> ({m.name})</span>}
          </h3>
          {debug && <div style={{ fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4 }}>
            {m.img_name || m.sl_base_name || m.name}.webp | 共 {totalCoords} 个位置 | 范围: ±{range}
          </div>}
          {debug && <div style={{ fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4, lineHeight: 1.4 }}>
            sl_base: {m.sl_base_name}<br />
            旋转:{m.rotate} 偏移:({m.offset_x},{m.offset_y}) 大小:{sx}x{sy} 组:{groupLabel}
          </div>}
          {debug && (
            <div style={{ fontSize: 11, color: "#aaa", marginBottom: 4, display: "flex", flexDirection: "column", gap: 3 }}>
              <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <span style={{ color: "#888" }}>范围:</span>
                <button onClick={() => setAdjField("range", Math.round(range / 2) - baseRange)} style={ctrlBtn}>÷2</button>
                <input type="number" value={range} onChange={e => setAdjField("range", Number(e.target.value) - baseRange)} style={ctrlInput} step={100} />
                <button onClick={() => setAdjField("range", range * 2 - baseRange)} style={ctrlBtn}>x2</button>
                <span style={{ color: "#aaa", fontSize: 12, marginLeft: 4 }}>↻{adj.rotate}</span>
              </div>
              <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <span style={{ color: "#888" }}>偏移:</span>
                <button onClick={() => setAdjField("y", adj.y - 50)} style={ctrlBtn}>↑</button>
                <button onClick={() => setAdjField("y", adj.y + 50)} style={ctrlBtn}>↓</button>
                <button onClick={() => setAdjField("x", adj.x - 50)} style={ctrlBtn}>←</button>
                <button onClick={() => setAdjField("x", adj.x + 50)} style={ctrlBtn}>→</button>
                <span style={{ color: "#888", marginLeft: 8 }}>X:</span>
                <input type="number" value={offX} onChange={e => setAdjField("x", Number(e.target.value) - (m.offset_x || 0))} style={ctrlInput} step={10} />
                <span style={{ color: "#888" }}>Y:</span>
                <input type="number" value={offY} onChange={e => setAdjField("y", Number(e.target.value) - (m.offset_y || 0))} style={ctrlInput} step={10} />
              </div>
              <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <button onClick={() => setAdjField("rotate", (adj.rotate + 1) % 4)} style={ctrlBtn}>↻ 旋转</button>
                <button onClick={() => setAdjField("mirrorX", !adj.mirrorX)} style={{ ...ctrlBtn, background: adj.mirrorX ? "#4CAF50" : "#555" }}>⇄ 左右</button>
                <button onClick={() => setAdjField("mirrorY", !adj.mirrorY)} style={{ ...ctrlBtn, background: adj.mirrorY ? "#4CAF50" : "#555" }}>⇅ 上下</button>
                <button onClick={() => setAdjOffsets(prev => { const n = { ...prev }; delete n[m.name]; return n; })} style={ctrlBtn}>↺ 重置</button>
              </div>
            </div>
          )}
          <div style={{
            aspectRatio: `${sx} / ${sy}`,
            background: "#2c2c2c", border: "1px solid #666", borderRadius: 4,
            position: "relative", overflow: "hidden",
            backgroundImage: `url(./data/img/${m.img_name || m.sl_base_name || 'RareModule_1x1'}.webp)`,
            backgroundSize: "cover", backgroundPosition: "center",
          }}>
            {dots.map((d, i) => {
              const [x, y] = applyTransform(d.x, d.y, offX, offY, adj);
              const [px, py] = computePixel(x, y, range, sx, sy);
              const col = d.entity.color;
              const zcol = zColor(d.z);
              const textCol = zcol === "#ff3333" ? "#ffffff" : zcol;
              const textShadow = zcol === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW;
              return (
                <div key={i} title={d.entity.name} style={{
                  position: "absolute", left: `${px}%`, top: `${py}%`,
                  width: 9, height: 9, borderRadius: "50%", background: col,
                  boxShadow: `0 0 6px ${col}`, border: "1px solid #fff",
                  transform: "translate(-50%, -50%)", zIndex: 10,
                }}>
                  <span style={{
                    position: "absolute", left: "50%", top: "100%",
                    transform: "translateX(-50%)", fontSize: 11,
                    fontFamily: "Arial, sans-serif", color: textCol,
                    whiteSpace: "nowrap", textShadow, lineHeight: 1, marginTop: 1,
                  }}>{Math.round(d.z)}</span>
                </div>
              );
            })}
          </div>
          {dots.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 10px", justifyContent: "center", marginTop: 5, fontSize: 13, color: "#ccc", alignItems: "center" }}>
              {[...new Set(dots.map(d => d.entity.name))].map(en => {
                const e = entities.find(x => x.name === en)!;
                return (
                  <span key={en} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                    <span style={{ width: 10, height: 10, borderRadius: "50%", background: e.color, flexShrink: 0 }}></span>
                    <span style={{ cursor: "pointer" }} onClick={() => toggle(en)}>{e.name}</span>
                    <span style={{ color: "#888" }}>({dots.filter(d => d.entity.name === en).length}点)</span>
                  </span>
                );
              })}
            </div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 10px", justifyContent: "center", marginTop: 8, fontSize: 13, color: "#ccc", alignItems: "center" }}>
            <span>名称: {m.name}</span>
            <span>大小: {sx}x{sy}</span>
            <span>旋转: {m.rotate} ({m.rotate * 90}°)</span>
            <span>偏移: ({m.offset_x}, {m.offset_y})</span>
            <span>范围: ±{baseRange}</span>
          </div>
        </div>
      </div>

      {debug && (() => {
        const rows = entities.filter(e => !hidden.has(e.name)).flatMap(e =>
          e.coords.map((c, j) => {
            const rowKey = `${e.name}-${j}`;
            return {
              key: rowKey,
              group: groupLabel,
              monster: { name: e.name, translation: e.name, color: e.color, onToggle: () => toggle(e.name) },
              file: "",
              mapName: m.name,
              mapLabel: m.translation || m.name,
              label: c.version || "",
              x: c.x,
              y: c.y,
              z: c.z,
              hidden: hiddenRows.has(rowKey),
            };
          })
        );
        return <DebugCoordTable rows={rows} onToggleRow={(key) => {
          setHiddenRows(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
          });
        }}
          onToggleMap={(mapName) => {
            const mapRows = rows.filter(r => r.mapName === mapName);
            const allHidden = mapRows.every(r => r.hidden);
            for (const r of mapRows) {
              if (allHidden) { setHiddenRows(prev => { const n = new Set(prev); n.delete(r.key); return n; }); }
              else if (!hiddenRows.has(r.key)) { setHiddenRows(prev => { const n = new Set(prev); n.add(r.key); return n; }); }
            }
          }} showMonster />;
      })()}

      <div style={{ marginTop: 10, padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 15, textAlign: "center", color: "#aaa" }}>
        <strong>位置统计：共 {totalCoords} 个位置点</strong>
        {entities.length > 0 && <><br /><strong>包含实体：</strong> {entities.map(e => `${e.name}(${e.coords.length})`).join("、")}</>}
      </div>
    </div>
  );
}
