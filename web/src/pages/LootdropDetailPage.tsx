import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { useDebug } from "../hooks/useDebug";
import { useSSRData } from "../context/SSRDataContext";
import { getAdj, applyTransform, computePixel, ctrlBtn, ctrlInput, type AdjState } from "../components/MapDebug";
import Disclaimer from "../components/Disclaimer";
import DebugCoordTable from "../components/DebugCoordTable";

interface LootdropCoord {
  x: number; y: number; z: number; map: string; file: string; version: string; label?: string;
}

interface LootdropMonster {
  name: string; translation: string; color: string; coords: LootdropCoord[];
}

interface LootdropItem {
  name: string; translation: string; monsters: LootdropMonster[];
}

interface DungeonModule {
  name: string; translation: string; group: string;
  size_x: number; size_y: number; sl_base_name: string; img_name: string;
  offset_x: number; offset_y: number; rotate: number; range: number;
}

const GROUP_LABELS: Record<string, string> = {
  Crypt: "废墟2层地牢", FireDeep: "哥布林洞穴2层", GoblinCave: "哥布林洞穴1层",
  IceAbyss: "冰图2层", IceCavern: "冰图1层", Inferno: "废墟3层炼狱",
  Ruins: "废墟1层", ShipGraveyard: "水图",
};

function zColor(z: number): string {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff3333";
}

const GLOW = "0 0 4px #fff, 0 0 2px #000";

export default function LootdropDetailPage() {
  const { name } = useParams<{ name: string }>();
  const dataKey = `lootdrops/${name ? decodeURIComponent(name) : ""}`;
  const ssrData = useSSRData<{ item: LootdropItem; modules: DungeonModule[] }>(dataKey);
  const [data, setData] = useState<LootdropItem | null>(ssrData?.item || null);
  const [modules, setModules] = useState<Map<string, DungeonModule>>(
    ssrData?.modules ? new Map(ssrData.modules.map((m: DungeonModule) => [m.name, m])) : new Map()
  );
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hiddenRows, setHiddenRows] = useState<Set<string>>(new Set()); // per-coord toggle: \"monsterName-index\"
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();

  useEffect(() => {
    if (!name) return;
    Promise.all([
      fetch(`./data/json/lootdrops/${decodeURIComponent(name)}.json`).then<LootdropItem>(r => r.json()),
      fetch(`./data/json/dungeon_modules.json`).then<DungeonModule[]>(r => r.json()),
    ])
      .then(([item, mods]) => {
        setData(item);
        const mm = new Map<string, DungeonModule>();
        mods.forEach(m => { mm.set(m.name, m); mm.set(m.sl_base_name, m); });
        setModules(mm);
      })
      .catch(console.error);
  }, [name]);

  if (!data) return <div style={{ textAlign: "center", color: "#ff6b6b", marginTop: 100 }}>未找到</div>;

  function myGetAdj(mapName: string, mod: DungeonModule | undefined) {
    return getAdj(mapName, mod?.rotate, adjOffsets);
  }

  function setAdj(mapName: string, field: string, value: number | boolean) {
    setAdjOffsets((prev: AdjState) => {
      const cur = prev[mapName] || {x: 0, y: 0, range: 0, rotate: 0, mirrorX: false, mirrorY: false};
      return {...prev, [mapName]: {...cur, [field]: value}};
    });
  }

  const toggle = (monsterName: string) => {
    setHidden(prev => {
      const next = new Set(prev);
      if (next.has(monsterName)) next.delete(monsterName);
      else next.add(monsterName);
      return next;
    });
  };

  const toggleRow = (key: string) => {
    setHiddenRows(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const monsters = data.monsters ?? [];
  // Build per-map coordinate groups
  const mapGroups = new Map<string, {mod: DungeonModule | undefined; dots: {monster: LootdropMonster; x: number; y: number; z: number; file: string}[]}>();
  for (const m of monsters) {
    if (hidden.has(m.name)) continue;
    for (const c of m.coords) {
      if (!mapGroups.has(c.map)) mapGroups.set(c.map, {mod: modules.get(c.map), dots: []});
      mapGroups.get(c.map)!.dots.push({monster: m, x: c.x, y: c.y, z: c.z, file: c.file});
    }
  }

  // Group by module group
  const groupedByType = new Map<string, typeof items>();
  // ... using same pattern as DetailPage
  const items = [...mapGroups.entries()].map(([mapName, {mod, dots}]) => ({mapName, mod, dots}));
  items.sort((a, b) => {
    const sy_a = a.mod?.size_y ?? 1;
    const sy_b = b.mod?.size_y ?? 1;
    const sx_a = a.mod?.size_x ?? 1;
    const sx_b = b.mod?.size_x ?? 1;
    return sy_a - sy_b || sx_a - sx_b;
  });
  for (const item of items) {
    const g = item.mod?.group || "";
    if (!groupedByType.has(g)) groupedByType.set(g, []);
    groupedByType.get(g)!.push(item);
  }

  const groupOrder = Object.keys(GROUP_LABELS);
  const sortedGroups = [...groupedByType.entries()].sort(([a], [b]) => groupOrder.indexOf(a) - groupOrder.indexOf(b));

  const totalCoords = monsters.reduce((s, m) => s + (hidden.has(m.name) ? 0 : m.coords.length), 0);
  const visibleCount = monsters.filter(m => !hidden.has(m.name)).length;

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
        <title>{data.translation || data.name} 掉落来源 | DarkFindV5游戏导航</title>
        <meta name="description" content="{data.translation || data.name} 由 {visibleCount} 个怪物掉落，共 {totalCoords} 个位置点。" />
        <meta property="og:title" content="{data.translation || data.name} 掉落来源 | DarkFindV5" />
        <meta property="og:description" content="{data.translation || data.name} 由 {visibleCount} 个怪物掉落" />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 28, margin: "0 0 8px" }}>
        {data.translation} &gt;&gt; {monsters.filter(m => !hidden.has(m.name)).map(m => m.translation).join("、")}
        {monsters.length - visibleCount > 0 && <span style={{ color: "#888", fontSize: 16 }}> (+{monsters.length - visibleCount})</span>}
        <span style={{ color: "#aaa", fontSize: 14, marginLeft: 12 }}>{monsters.length}种坐标汇总</span>
      </h1>

      <Disclaimer />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", margin: "15px 0", padding: 10, background: "#3a3a3a", borderRadius: 5 }}>
        <button onClick={() => {
          const allHidden = monsters.every(m => hidden.has(m.name));
          if (allHidden || hidden.size === monsters.length) {
            setHidden(new Set());
          } else {
            setHidden(new Set(monsters.map(m => m.name)));
          }
        }} style={{
          padding: "8px 15px", border: "2px solid #888", borderRadius: 5,
          cursor: "pointer", fontSize: 14, fontWeight: "bold", color: "#ccc",
          background: "transparent", transition: "all 0.2s",
        }}>
          {hidden.size === 0 ? "隐藏全部" : "全部显示"}
        </button>
        {monsters.map(m => (
          <button key={m.name} onClick={() => toggle(m.name)} style={{
            padding: "8px 15px", border: `2px solid ${m.color}`, borderRadius: 5,
            cursor: "pointer", fontSize: 14, fontWeight: "bold", color: "#fff",
            background: hidden.has(m.name) ? "transparent" : m.color,
            opacity: hidden.has(m.name) ? 0.3 : 1,
            transition: "all 0.2s",
          }}>{m.translation} ({m.coords.length})</button>
        ))}
      </div>

      {debug && (
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center", margin: "10px 0", padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 14, color: "#aaa" }}>
        <strong style={{ color: "#ccc" }}>怪物图例：</strong>
        {monsters.map(m => (
          <span key={m.name} style={{ display: "flex", alignItems: "center", gap: 5, cursor: "pointer", opacity: hidden.has(m.name) ? 0.3 : 1 }} onClick={() => toggle(m.name)}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: m.color }}></span>
            {m.translation} <span style={{ color: "#888" }}>({m.coords.length})</span>
          </span>
        ))}
      </div>
      )}

      <div style={{ display: "grid", gap: 6, gridTemplateColumns: "repeat(4, 1fr)" }}>
        {sortedGroups.map(([groupName, groupItems]) => (
          <>
            {groupName && <div key={`h-${groupName}`} style={{ gridColumn: "1 / -1", fontSize: 22, fontWeight: "bold", color: "#FFC107", padding: "5px 0", marginTop: 10, borderBottom: "2px solid #FFC107" }}>{GROUP_LABELS[groupName] || groupName}</div>}
            {groupItems.map(({mapName, mod, dots}) => {
              const sx = mod?.size_x ?? 1;
              const sy = mod?.size_y ?? 1;
              const baseRange = mod?.range || Math.max(sx, sy) * 1600 || 1600;
              const adj = myGetAdj(mapName, mod);
              const range = (baseRange + adj.range) || 1600;
              const offX = (mod?.offset_x ?? 0) + adj.x;
              const offY = (mod?.offset_y ?? 0) + adj.y;
              return (
                <div key={mapName} style={{ minWidth: 0, gridColumn: sx >= 2 ? `span ${sx}` : undefined, gridRow: sy >= 2 ? `span ${sy}` : undefined, background: "#3a3a3a", border: "1px solid #555", borderRadius: 5, padding: 8 }}>
                  <h3 style={{ margin: "0 0 6px 0", fontSize: 22, color: "#00bcd4", textAlign: "center", width: "100%", lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {mod?.translation || mapName}
                    {debug && <span style={{ color: "#888", fontSize: 11 }}> ({mapName})</span>}
                  </h3>
                  {debug && <div style={{ fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4 }}>
                    {mod?.img_name || mod?.sl_base_name || mapName}.webp | 找到 {dots.length} 个位置 | 范围: ±{range}
                  </div>}
                  {debug && <div style={{ fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4, lineHeight: 1.4 }}>
                    {dots[0]?.file || ""}<br/>
                    旋转:{mod?.rotate ?? 0} 偏移:({mod?.offset_x ?? 0},{mod?.offset_y ?? 0}) 大小:{sx}x{sy}
                  </div>}
                  {debug && (
                  <div style={{ fontSize: 11, color: "#aaa", marginBottom: 4, display: "flex", flexDirection: "column", gap: 3 }}>
                    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      <span style={{ color: "#888" }}>范围:</span>
                      <button onClick={() => setAdj(mapName, "range", Math.round(range / 2) - baseRange)} style={ctrlBtn}>÷2</button>
                      <input type="number" value={range} onChange={e => setAdj(mapName, "range", Number(e.target.value) - baseRange)} style={ctrlInput} step={100} />
                      <button onClick={() => setAdj(mapName, "range", range * 2 - baseRange)} style={ctrlBtn}>x2</button>
                      <span style={{ color: "#aaa", fontSize: 12, marginLeft: 4 }}>↻{adj.rotate}</span>
                    </div>
                    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      <span style={{ color: "#888" }}>偏移:</span>
                      <button onClick={() => setAdj(mapName, "y", adj.y - 50)} style={ctrlBtn}>↑</button>
                      <button onClick={() => setAdj(mapName, "y", adj.y + 50)} style={ctrlBtn}>↓</button>
                      <button onClick={() => setAdj(mapName, "x", adj.x - 50)} style={ctrlBtn}>←</button>
                      <button onClick={() => setAdj(mapName, "x", adj.x + 50)} style={ctrlBtn}>→</button>
                      <span style={{ color: "#888", marginLeft: 8 }}>X:</span>
                      <input type="number" value={offX} onChange={e => setAdj(mapName, "x", Number(e.target.value) - (mod?.offset_x ?? 0))} style={ctrlInput} step={10} />
                      <span style={{ color: "#888" }}>Y:</span>
                      <input type="number" value={offY} onChange={e => setAdj(mapName, "y", Number(e.target.value) - (mod?.offset_y ?? 0))} style={ctrlInput} step={10} />
                    </div>
                    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      <button onClick={() => setAdj(mapName, "rotate", (adj.rotate + 1) % 4)} style={ctrlBtn}>↻ 旋转</button>
                      <button onClick={() => setAdj(mapName, "mirrorX", !adj.mirrorX)} style={{...ctrlBtn, background: adj.mirrorX ? "#4CAF50" : "#555"}}>⇄ 左右</button>
                      <button onClick={() => setAdj(mapName, "mirrorY", !adj.mirrorY)} style={{...ctrlBtn, background: adj.mirrorY ? "#4CAF50" : "#555"}}>⇅ 上下</button>
                      <button onClick={() => setAdjOffsets(prev => { const n = {...prev}; delete n[mapName]; return n; })} style={ctrlBtn}>↺ 重置</button>
                    </div>
                  </div>
                   )}
                  <div style={{ aspectRatio: `${sx} / ${sy}`, background: "#2c2c2c", border: "1px solid #666", borderRadius: 4, position: "relative", overflow: "hidden", backgroundImage: `url(./data/img/${mod?.img_name || mod?.sl_base_name || 'RareModule_1x1'}.webp)`, backgroundSize: "cover", backgroundPosition: "center" }}>
                    {dots.map((d, i) => {
                      const [x, y] = applyTransform(d.x, d.y, offX, offY, adj);
                      const [px, py] = computePixel(x, y, range, sx, sy);
                      const col = d.monster.color;
                      const zcol = zColor(d.z);
                      const textCol = zcol === "#ff3333" ? "#ffffff" : zcol;
                      const textShadow = zcol === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW;
                      return (
                        <div key={i} title={d.monster.translation} style={{ position: "absolute", left: `${px}%`, top: `${py}%`, width: 9, height: 9, borderRadius: "50%", background: col, boxShadow: `0 0 6px ${col}`, border: "1px solid #fff", transform: "translate(-50%, -50%)", zIndex: 10 }}>
                          <span style={{ position: "absolute", left: "50%", top: "100%", transform: "translateX(-50%)", fontSize: 11, fontFamily: "Arial, sans-serif", color: textCol, whiteSpace: "nowrap", textShadow, lineHeight: 1, marginTop: 1 }}>{Math.round(d.z)}</span>
                        </div>
                      );
                    })}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 10px", justifyContent: "center", marginTop: 5, fontSize: 13, color: "#ccc", alignItems: "center" }}>
                    {[...new Set(dots.map(d => d.monster.name))].map(mn => {
                      const m = monsters.find(x => x.name === mn)!;
                      return (
                        <span key={mn} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                          <span style={{ width: 10, height: 10, borderRadius: "50%", background: m.color, flexShrink: 0 }}></span>
                          <span style={{ cursor: "pointer" }} onClick={() => toggle(mn)}>{m.translation}</span>
                          <span style={{ color: "#888" }}>({dots.filter(d => d.monster.name === mn).length}点)</span>
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

      {debug && (() => {
        const rows = monsters.filter(m => !hidden.has(m.name)).flatMap(m =>
          m.coords.map((c, j) => {
            const mod = modules.get(c.map);
            const g = mod?.group || "";
            const rowKey = `${m.name}-${j}`;
            return {
              key: rowKey,
              group: GROUP_LABELS[g] || g,
              monster: { name: m.name, translation: m.translation, color: m.color, onToggle: () => toggle(m.name) },
              file: c.file,
              mapName: c.map,
              mapLabel: mod?.translation || c.map,
              label: c.label || "",
              x: c.x,
              y: c.y,
              z: c.z,
              hidden: hiddenRows.has(rowKey),
            };
          })
        );
        return <DebugCoordTable rows={rows} onToggleRow={toggleRow}
          onToggleMap={(mapName) => {
            const mapRows = rows.filter(r => r.mapName === mapName);
            const allHidden = mapRows.every(r => r.hidden);
            for (const r of mapRows) {
              if (allHidden) toggleRow(r.key);
              else if (hiddenRows.has(r.key)) {} // already hidden
              else toggleRow(r.key);
            }
          }} showMonster />;
      })()}

      <div style={{ marginTop: 10, padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 15, textAlign: "center", color: "#aaa" }}>
        <strong>位置统计：共 {totalCoords} 个位置点</strong>
        <br /><strong>包含地图：</strong> {[...new Set([...mapGroups.keys()])].map(k => modules.get(k)?.translation || k).join("、")}
      </div>
    </div>
  );
}
