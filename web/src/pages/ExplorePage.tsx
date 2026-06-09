import { useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Spin } from "antd";

interface ExploreTarget {
  name: string;
  module_name: string;
  quest_title: string;
  npc_name: string;
  npc_name_display: string;
  quest_number: number;
}

export default function ExplorePage() {
  const [data, setData] = useState<ExploreTarget[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("./data/json/explore.json")
      .then((r) => r.json())
      .then(setData)
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
        <meta name="description" content="探索目标汇总——{data.length} 个探索目标，分布在 {grouped.size} 个NPC。" />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }}>
        【探索地点表】探索目标汇总
      </h1>
      <div style={{ textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }}>
        共 {data.length} 个探索目标，分布在 {grouped.size} 个NPC
      </div>
      {[...grouped.entries()].map(([npcName, targets]) => (
        <div key={npcName} style={{ marginBottom: 24 }}>
          <div style={{
            fontSize: 22, fontWeight: "bold", color: "#FFC107",
            padding: "5px 0", borderBottom: "2px solid #FFC107", marginBottom: 12,
          }}>
            {npcName} ({targets.length})
          </div>
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16,
          }}>
            {targets.map((t, i) => (
              <div key={i} style={{
                background: "#3a3a3a", border: "1px solid #555", borderRadius: 8,
                padding: 16, cursor: "pointer",
                transition: "transform 0.2s",
              }}
              onMouseEnter={e => e.currentTarget.style.transform = "translateY(-3px)"}
              onMouseLeave={e => e.currentTarget.style.transform = "none"}
              >
                <div style={{ color: "#00bcd4", fontSize: 16, fontWeight: "bold", marginBottom: 6 }}>
                  {t.name || t.module_name}
                </div>
                <div style={{ color: "#aaa", fontSize: 12 }}>
                  任务: {t.quest_title || `#${t.quest_number}`}
                </div>
                <div style={{ color: "#888", fontSize: 11, marginTop: 4 }}>
                  {t.module_name}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
