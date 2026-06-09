import { useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Tag } from "antd";
import { useSSRData } from "../context/SSRDataContext";

interface QuestReward {
  type: string;
  id: string;
  count: number;
}

interface NPCQuest {
  id: string;
  title: string;
  quest_number: number;
  greeting: string;
  complete: string;
  rewards: QuestReward[];
  required: string;
}

interface NPCEntry {
  npc_name: string;
  npc_name_display: string;
  quest_count: number;
  category: string;
  quests: NPCQuest[];
}

export default function QuestNPCPage() {
  const ssrData = useSSRData<NPCEntry[]>("quest_npc");
  const [data, setData] = useState<NPCEntry[]>(ssrData || []);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (ssrData) return;
    fetch("./data/json/quest_npc.json")
      .then((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Helmet>
        <title>任务NPC表 | DarkFindV5游戏导航</title>
        <meta name="description" content="NPC任务详情查询——查看各NPC的任务、奖励、需求。" />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }}>
        【任务NPC表】NPC任务详情
      </h1>
      <div style={{ textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }}>
        共 {data.length} 个活跃NPC
      </div>
      {(() => {
        const grouped = new Map<string, NPCEntry[]>();
        for (const npc of data) {
          const cat = npc.category || "其他";
          if (!grouped.has(cat)) grouped.set(cat, []);
          grouped.get(cat)!.push(npc);
        }
        const order = ["装备NPC", "优选NPC", "可用NPC", ""];
        return [...grouped.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
      })().map(([category, npcs]) => (<div key={category}>
        <div style={{
          fontSize: 22, fontWeight: "bold", color: "#FFC107",
          padding: "5px 0", borderBottom: "2px solid #FFC107", marginBottom: 12, marginTop: 24,
        }}>
          {category || "其他"} ({npcs.length})
        </div>
        {npcs.map((npc) => (
        <div key={npc.npc_name} style={{
          background: "#3a3a3a", border: "1px solid #555", borderRadius: 8,
          padding: 16, marginBottom: 16, cursor: "pointer",
        }}
        onClick={() => setExpanded(expanded === npc.npc_name ? null : npc.npc_name)}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ color: "#00bcd4", fontSize: 20, fontWeight: "bold" }}>
              {npc.npc_name_display}
            </div>
            <div style={{ color: "#aaa", fontSize: 13 }}>
              {npc.quest_count} 个任务
            </div>
          </div>
          {expanded === npc.npc_name && (
            <div style={{ marginTop: 12 }}>
              {npc.quests.map((q) => (
                <div key={q.id} style={{
                  background: "#2c2c2c", border: "1px solid #444", borderRadius: 6,
                  padding: 12, marginBottom: 8,
                }}>
                  <div style={{ color: "#FFC107", fontWeight: "bold", marginBottom: 4 }}>
                    #{q.quest_number} {q.title}
                  </div>
                  {q.greeting && (
                    <div style={{ color: "#aaa", fontSize: 12, marginBottom: 4 }}>
                      接取: {q.greeting}
                    </div>
                  )}
                  {q.complete && (
                    <div style={{ color: "#aaa", fontSize: 12, marginBottom: 4 }}>
                      完成: {q.complete}
                    </div>
                  )}
                  {q.rewards.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      {q.rewards.map((r, ri) => (
                        <Tag key={ri} color="green" style={{ fontSize: 11 }}>
                          {r.id} ×{r.count}
                        </Tag>
                      ))}
                    </div>
                  )}
                  {q.required && (
                    <div style={{ color: "#888", fontSize: 11, marginTop: 4 }}>
                      前置: {q.required}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      </div>
      ))}
    </div>
  );
}
