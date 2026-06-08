import { useEffect, useState } from "react";
import { Spin } from "antd";
import { useNavigate } from "react-router-dom";
import type { IndexEntry } from "../types/data";

const CARD_THEME: Record<string, { border: string; hoverBg: string; icon: string; titleColor: string }> = {
  items:    { border: "#4CAF50", hoverBg: "linear-gradient(145deg, #2a4a2a, #3a5a3a)", icon: "📦", titleColor: "#fff" },
  monsters: { border: "#FF6600", hoverBg: "linear-gradient(145deg, #4a3a2a, #5a4a3a)", icon: "👹", titleColor: "#fff" },
  props:    { border: "#9C27B0", hoverBg: "linear-gradient(145deg, #3a2a4a, #4a3a5a)", icon: "🏛️", titleColor: "#CE93D8" },
  lootdrops: { border: "#2196F3", hoverBg: "linear-gradient(145deg, #2a3a4a, #3a4a5a)", icon: "💎", titleColor: "#fff" },
  explore: { border: "#00bcd4", hoverBg: "linear-gradient(145deg, #2a4a4a, #3a5a5a)", icon: "🗺️", titleColor: "#00bcd4" },
  quest_items: { border: "#E91E63", hoverBg: "linear-gradient(145deg, #4a2a3a, #5a3a4a)", icon: "📋", titleColor: "#F06292" },
  quest_npc: { border: "#FFC107", hoverBg: "linear-gradient(145deg, #4a4a2a, #5a5a3a)", icon: "🗡️", titleColor: "#FFD54F" },
};

const DEFAULT_THEME = { border: "#555", hoverBg: "linear-gradient(145deg, #3a3a3a, #444)", icon: "📄", titleColor: "#fff" };

export default function HomePage() {
  const [data, setData] = useState<IndexEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("./data/index.json")
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }}>
        DarkFindV5游戏导航
      </h1>
      <div style={{
        textAlign: "center", color: "#ff6b6b", fontSize: 16, marginBottom: 30,
        padding: 10, background: "#3a3a3a", borderRadius: 5, maxWidth: 700, marginLeft: "auto", marginRight: "auto",
      }}>
        ⚠️ 数据有误差，以实际游戏内为准
      </div>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 20,
      }}>
        {data.map((entry) => {
          const t = CARD_THEME[entry.page] ?? DEFAULT_THEME;
          return (
            <div
              key={entry.page}
              onClick={() => navigate(`/${entry.page}`)}
              style={{
                background: "linear-gradient(145deg, #3a3a3a, #444444)",
                border: `2px solid ${t.border}`,
                borderRadius: 16,
                padding: "30px 20px",
                textAlign: "center",
                cursor: "pointer",
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                boxShadow: "0 4px 6px rgba(0,0,0,0.3)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = t.hoverBg;
                e.currentTarget.style.transform = "translateY(-8px) scale(1.02)";
                e.currentTarget.style.boxShadow = "0 12px 24px rgba(0,0,0,0.5)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "linear-gradient(145deg, #3a3a3a, #444444)";
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow = "0 4px 6px rgba(0,0,0,0.3)";
              }}
            >
              <div style={{ fontSize: 48, marginBottom: 8, filter: `drop-shadow(0 0 8px ${t.border})` }}>
                {t.icon}
              </div>
              <div style={{ color: "#fff", fontSize: 24, fontWeight: "bold", marginBottom: 4 }}>
                【{entry.label}】
              </div>
              <div style={{ color: t.titleColor, fontSize: 14 }}>
                {entry.label}{entry.count}个
              </div>
              <div style={{ color: "#888", fontSize: 14, marginTop: 4 }}>
                {entry.page === "items" && "查看物品位置"}
                {entry.page === "monsters" && "查看怪物位置"}
                {entry.page === "props" && "查看实体位置"}
                {entry.page === "lootdrops" && "查看物品掉落怪物"}
                {entry.page === "explore" && "地图模块预览"}
                {entry.page === "quest_items" && "按地图分组查看任务物品"}
                {entry.page === "quest_npc" && "查看NPC任务详情"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
