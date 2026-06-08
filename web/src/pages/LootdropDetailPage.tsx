import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Spin } from "antd";

interface LootdropCoord {
  x: number; y: number; z: number; map: string; file: string; version: string;
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
  const [data, setData] = useState<LootdropItem | null>(null);
  const [modules, setModules] = useState<Map<string, DungeonModule>>(new Map());
  const [loading, setLoading] = useState(true);
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!name) return;
    Promise.all([
      fetch(`./data/lootdrops/${decodeURIComponent(name)}.json`).then<LootdropItem>(r => r.json()),
      fetch(`./data/dungeon_modules.json`).then<DungeonModule[]>(r => r.json()),
    ])
      .then(([item, mods]) => {
        setData(item);
        setModules(new Map(mods.map(m => [m.sl_base_name, m])));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [name]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!data) return <div style={{ textAlign: "center", color: "#ff6b6b", marginTop: 100 }}>未找到</div>;

  const toggle = (monsterName: string) => {
    setHidden(prev => {
      const next = new Set(prev);
      if (next.has(monsterName)) next.delete(monsterName);
      else next.add(monsterName);
      return next;
    });
  };

  // Build per-map coordinate groups
  const mapGroups = new Map<string, {mod: DungeonModule | undefined; dots: {monster: LootdropMonster; x: number; y: number; z: number}[]}>();
  for (const m of data.monsters) {
    if (hidden.has(m.name)) continue;
    for (const c of m.coords) {
      if (!mapGroups.has(c.map)) mapGroups.set(c.map, {mod: modules.get(c.map), dots: []});
      mapGroups.get(c.map)!.dots.push({monster: m, x: c.x, y: c.y, z: c.z});
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

  const totalCoords = data.monsters.reduce((s, m) => s + (hidden.has(m.name) ? 0 : m.coords.length), 0);
  const visibleCount = data.monsters.filter(m => !hidden.has(m.name)).length;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 28, margin: "0 0 8px" }}>
        {data.translation} &gt;&gt; {data.monsters.filter(m => !hidden.has(m.name)).map(m => m.translation).join("、")}
        {data.monsters.length - visibleCount > 0 && <span style={{ color: "#888", fontSize: 16 }}> (+{data.monsters.length - visibleCount})</span>}
        <span style={{ color: "#aaa", fontSize: 14, marginLeft: 12 }}>怪物坐标汇总</span>
      </h1>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", margin: "15px 0", padding: 10, background: "#3a3a3a", borderRadius: 5 }}>
        {data.monsters.map(m => (
          <button key={m.name} onClick={() => toggle(m.name)} style={{
            padding: "8px 15px", border: `2px solid ${m.color}`, borderRadius: 5,
            cursor: "pointer", fontSize: 14, fontWeight: "bold", color: "#fff",
            background: hidden.has(m.name) ? "transparent" : m.color,
            opacity: hidden.has(m.name) ? 0.3 : 1,
            transition: "all 0.2s",
          }}>{m.translation} ({m.coords.length})</button>
        ))}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center", margin: "10px 0", padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 14, color: "#aaa" }}>
        <strong style={{ color: "#ccc" }}>怪物图例：</strong>
        {data.monsters.map(m => (
          <span key={m.name} style={{ display: "flex", alignItems: "center", gap: 5, cursor: "pointer", opacity: hidden.has(m.name) ? 0.3 : 1 }} onClick={() => toggle(m.name)}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: m.color }}></span>
            {m.translation} <span style={{ color: "#888" }}>({m.coords.length})</span>
          </span>
        ))}
      </div>

      <div style={{ textAlign: "center", color: "#ff6b6b", fontSize: 14, marginBottom: 20, padding: 8, background: "#3a3a3a", borderRadius: 5, maxWidth: 700, marginLeft: "auto", marginRight: "auto" }}>
        ⚠️ 数据有误差，以实际游戏内为准<span style={{ color: "#aaa", marginLeft: 15 }}>地图生成日期：2026-06-08 <span style={{ fontSize: 10 }}>地图页面设计-雪鸡Official</span></span>
      </div>

      <div style={{ display: "grid", gap: 6, gridTemplateColumns: "repeat(4, 1fr)" }}>
        {sortedGroups.map(([groupName, groupItems]) => (
          <>
            {groupName && <div key={`h-${groupName}`} style={{ gridColumn: "1 / -1", fontSize: 22, fontWeight: "bold", color: "#FFC107", padding: "5px 0", marginTop: 10, borderBottom: "2px solid #FFC107" }}>{GROUP_LABELS[groupName] || groupName}</div>}
            {groupItems.map(({mapName, mod, dots}) => {
              const sx = mod?.size_x ?? 1;
              const sy = mod?.size_y ?? 1;
              const range = mod?.range || Math.max(sx, sy) * 1600 || 1600;
              return (
                <div key={mapName} style={{ minWidth: 0, gridColumn: sx >= 2 ? `span ${sx}` : undefined, gridRow: sy >= 2 ? `span ${sy}` : undefined, background: "#3a3a3a", border: "1px solid #555", borderRadius: 5, padding: 8 }}>
                  <h3 style={{ margin: "0 0 6px 0", fontSize: 22, color: "#00bcd4", textAlign: "center", width: "100%", lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{mod?.translation || mapName}</h3>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 10px", justifyContent: "center", marginTop: 5, fontSize: 13, color: "#ccc", alignItems: "center" }}>
                    {[...new Set(dots.map(d => d.monster.name))].map(mn => {
                      const m = data.monsters.find(x => x.name === mn)!;
                      return (
                        <span key={mn} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                          <span style={{ width: 10, height: 10, borderRadius: "50%", background: m.color, flexShrink: 0 }}></span>
                          <span style={{ cursor: "pointer" }} onClick={() => toggle(mn)}>{m.translation}</span>
                          <span style={{ color: "#888" }}>{dots.filter(d => d.monster.name === mn).length}</span>
                        </span>
                      );
                    })}
                  </div>
                  <div style={{ aspectRatio: `${sx} / ${sy}`, background: "#2c2c2c", border: "1px solid #666", borderRadius: 4, position: "relative", overflow: "hidden", ...(mod?.img_name || mod?.sl_base_name ? { backgroundImage: `url(./data/img/${mod.img_name || mod.sl_base_name}.webp)`, backgroundSize: "cover", backgroundPosition: "center" } : {}) }}>
                    {dots.map((d, i) => {
                      const multX = sx === 1 && sy === 2 ? 100 : 50;
                      const centerX = sx === 1 && sy === 2 ? 100 : 50;
                      const px = centerX + (d.x / range) * multX;
                      const py = 50 + (d.y / range) * 50;
                      const col = d.monster.color;
                      const zcol = zColor(d.z);
                      return (
                        <div key={i} style={{ position: "absolute", left: `${px}%`, top: `${py}%`, width: 9, height: 9, borderRadius: "50%", background: col, boxShadow: `0 0 6px ${col}`, border: "1px solid #fff", transform: "translate(-50%, -50%)", zIndex: 10 }}>
                          <span style={{ position: "absolute", left: "50%", top: "100%", transform: "translateX(-50%)", fontSize: 11, fontFamily: "Arial, sans-serif", color: zcol, whiteSpace: "nowrap", textShadow: zcol === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW, lineHeight: 1, marginTop: 1 }}>{Math.round(d.z)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </>
        ))}
      </div>

      <div style={{ marginTop: 10, padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 15, textAlign: "center", color: "#aaa" }}>
        <strong>位置统计：共 {totalCoords} 个位置点</strong>
        <br /><strong>包含地图：</strong> {[...new Set([...mapGroups.keys()])].map(k => modules.get(k)?.translation || k).join("、")}
      </div>
    </div>
  );
}
