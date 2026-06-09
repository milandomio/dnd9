import { useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Spin } from "antd";
import { useSSRData } from "../context/SSRDataContext";

interface QuestItem {
  item_name: string;
  item_translation: string;
  npc_name: string;
  npc_name_cn: string;
  quest_number: number;
  count: number;
  rarity: string;
  is_loot: string;
}

export default function QuestItemsPage() {
  const ssrData = useSSRData<QuestItem[]>("quest_items");
  const [data, setData] = useState<QuestItem[]>(ssrData || []);
  const [loading, setLoading] = useState(!ssrData);

  useEffect(() => {
    if (ssrData) return;
    fetch("./data/json/quest_items.json")
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const grouped = new Map<string, QuestItem[]>();
  for (const t of data) {
    const key = t.npc_name_cn || t.npc_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(t);
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Helmet>
        <title>任务物品表 | DarkFindV5游戏导航</title>
        <meta name="description" content="任务物品查询——按地图分组查看任务物品分布。" />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }}>
        【任务物品表】任务物品汇总
      </h1>
      <div style={{ textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }}>
        共 {data.length} 个任务物品，分布在 {grouped.size} 个NPC
      </div>
      {[...grouped.entries()].map(([npcName, items]) => (
        <div key={npcName} style={{ marginBottom: 24 }}>
          <div style={{
            fontSize: 22, fontWeight: "bold", color: "#FFC107",
            padding: "5px 0", borderBottom: "2px solid #FFC107", marginBottom: 12,
          }}>
            {npcName} ({items.length})
          </div>
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12,
          }}>
            {items.map((qi, i) => (
              <div key={i} style={{
                background: "#3a3a3a", border: "1px solid #555", borderRadius: 6,
                padding: 12, fontSize: 13,
              }}>
                <div style={{ color: "#E91E63", fontWeight: "bold", marginBottom: 4 }}>
                  {qi.item_translation || qi.item_name}
                </div>
                <div style={{ color: "#aaa" }}>
                  任务 #{qi.quest_number} ×{qi.count}
                  {qi.rarity && <span style={{ marginLeft: 8, color: "#FFC107" }}>{qi.rarity}</span>}
                  {qi.is_loot && <span style={{ marginLeft: 8, color: "#4CAF50" }}>已拾取</span>}
                </div>
                <div style={{ color: "#888", fontSize: 11, marginTop: 2 }}>
                  {qi.item_name}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
