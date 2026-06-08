import { useEffect, useState } from "react";
import { Spin } from "antd";
import { useParams, useNavigate } from "react-router-dom";
interface IndexEntry {
  name: string;
  translation: string;
  category?: string;
  monsters?: string[];
  monster_translations?: string[];
  coordCount: number;
}

const LABEL_MAP: Record<string, string> = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
  lootdrops: "掉落表",
};

export default function ListPage() {
  const { page } = useParams<{ page: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<IndexEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [debug, setDebug] = useState(false);

  useEffect(() => {
    if (!page || !["items", "monsters", "props", "lootdrops"].includes(page)) return;
    fetch(`./data/${page}.json`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }}>
        【{LABEL_MAP[page!] ?? page}】实体位置汇总
      </h1>
      <div style={{ textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }}>
        有效实体{data.length}个
      </div>
      {debug && (
        <button onClick={() => setDebug(false)}
          style={{
            position: "fixed", top: 20, right: 20, padding: "10px 20px",
            background: "#4CAF50", color: "#fff", border: "2px solid #388E3C",
            borderRadius: 8, cursor: "pointer", fontSize: 14, fontWeight: "bold",
            zIndex: 9999, boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
          }}
        >退出调试</button>
      )}
      {!debug && (
        <button onClick={() => setDebug(true)}
          style={{
            position: "fixed", top: 20, right: 20, padding: "10px 20px",
            background: "#FFC107", color: "#000", border: "2px solid #FF9800",
            borderRadius: 8, cursor: "pointer", fontSize: 14, fontWeight: "bold",
            zIndex: 9999, boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
          }}
        >显示全部</button>
      )}
      <div className="section-content" style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 20,
      }}>
        {data.map((entity) => (
          <div
            key={entity.name}
            onClick={() => {
              if (page === "lootdrops") {
                // Lootdrops items navigate to items detail page
                navigate(`/lootdrops/${entity.name}`);
              } else {
                navigate(`/${page}/${entity.name}`);
              }
            }}
            style={{
              background: "#3a3a3a",
              border: "1px solid #555",
              borderRadius: 8,
              padding: 20,
              textAlign: "center",
              cursor: "pointer",
              transition: "transform 0.2s, box-shadow 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-5px)";
              e.currentTarget.style.boxShadow = "0 5px 15px rgba(0,0,0,0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "none";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <div style={{ color: "#fff", fontSize: 18, fontWeight: "bold" }}>
              {entity.translation || entity.name}
            </div>
            {debug && (
              <div style={{ color: "#888", fontSize: 12, marginTop: 4 }}>
                {entity.translation}【{entity.name}】
              </div>
            )}
            {entity.monsters && entity.monsters.length > 0 && page === "lootdrops" && (
              <div style={{ color: "#aaa", fontSize: 13, marginTop: 6 }}>
                掉落来源({entity.monsters.length}个): {entity.monster_translations?.join("、") || entity.monsters.join("、")}
              </div>
            )}
            {entity.monsters && entity.monsters.length > 0 && page !== "lootdrops" && (
              <div style={{ color: "#aaa", fontSize: 13, marginTop: 6 }}>
                掉落来源: {entity.monsters.length}个
              </div>
            )}
            </div>
        ))}
      </div>
    </div>
  );
}
