import { useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Spin } from "antd";
import { useSSRData } from "../context/SSRDataContext";
import type { DungeonModule } from "../types/data";

interface ExploreTarget {
  name: string;
  module_name: string;
  quest_title: string;
  npc_name: string;
  npc_name_display: string;
  quest_number: number;
}

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

function modKey(module_name: string): string {
  return module_name.replace(/^Id_DungeonModule_/, "");
}

export default function ExplorePage() {
  const ssrData = useSSRData<ExploreTarget[]>("explore");
  const [data, setData] = useState<ExploreTarget[]>(ssrData || []);
  const [modules, setModules] = useState<Map<string, DungeonModule>>(new Map());
  const [loading, setLoading] = useState(!ssrData);

  useEffect(() => {
    Promise.all([
      ssrData ? Promise.resolve(ssrData) : fetch("./data/json/explore.json").then<ExploreTarget[]>((r) => r.json()),
      fetch("./data/json/dungeon_modules.json").then<DungeonModule[]>((r) => r.json()),
    ])
      .then(([exp, mods]) => {
        if (!ssrData) setData(exp);
        const mm = new Map<string, DungeonModule>();
        mods.forEach((m) => { mm.set(m.name, m); mm.set(m.sl_base_name, m); });
        setModules(mm);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const grouped = new Map<string, ExploreTarget[]>();
  for (const t of data) {
    const key = t.npc_name_display || t.npc_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(t);
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Helmet>
        <title>探索地点表 | DarkFindV5游戏导航</title>
        <meta name="description" content={`探索目标汇总——${data.length} 个探索目标，分布在 ${grouped.size} 个NPC。`} />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }}>
        【探索地点表】探索目标汇总
      </h1>
      <div style={{ textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }}>
        共 {data.length} 个探索目标，分布在 {grouped.size} 个NPC
      </div>
      {[...grouped.entries()].map(([npcName, targets]) => {
        const sorted = [...targets].sort((a, b) => a.quest_number - b.quest_number);
        return (
          <div key={npcName} style={{ marginBottom: 24 }}>
            <div style={{
              fontSize: 22, fontWeight: "bold", color: "#FFC107",
              padding: "5px 0", borderBottom: "2px solid #FFC107", marginBottom: 12,
            }}>
              {npcName} ({targets.length})
            </div>
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8,
            }}>
              {sorted.map((t, i) => {
                const mk = modKey(t.module_name);
                const mod = modules.get(mk);
                const sx = mod?.size_x ?? 1;
                const sy = mod?.size_y ?? 1;
                const groupLabel = mod?.group ? GROUP_LABELS[mod.group] : "";
                return (
                  <div key={i} style={{
                    minWidth: 0,
                    gridColumn: sx >= 2 ? `span ${sx}` : undefined,
                    gridRow: sy >= 2 ? `span ${sy}` : undefined,
                    background: "#3a3a3a",
                    border: "1px solid #555",
                    borderRadius: 5,
                    padding: 8,
                  }}>
                    <h3 style={{
                      margin: "0 0 2px 0",
                      fontSize: 22,
                      color: "#00bcd4",
                      textAlign: "center",
                      width: "100%",
                      lineHeight: 1.3,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}>
                      {groupLabel && <span style={{ color: "#FFC107", fontSize: 13, fontWeight: "normal" }}>[{groupLabel}] </span>}
                      {t.name || mk}
                    </h3>
                    <div style={{
                      fontSize: 13, color: "#aaa", marginBottom: 5, textAlign: "center",
                    }}>
                      {npcName} - 任务: {t.quest_title || `#${t.quest_number}`}
                    </div>
                    <div style={{
                      aspectRatio: `${sx} / ${sy}`,
                      background: "#2c2c2c",
                      border: "1px solid #666",
                      borderRadius: 4,
                      position: "relative",
                      overflow: "hidden",
                      backgroundImage: `url(./data/img/${mod?.img_name || mod?.sl_base_name || 'RareModule_1x1'}.webp)`,
                      backgroundSize: "cover",
                      backgroundPosition: "center",
                    }} />
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
