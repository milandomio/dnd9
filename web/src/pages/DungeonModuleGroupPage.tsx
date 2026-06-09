import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
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

export default function DungeonModuleGroupPage() {
  const { group } = useParams<{ group: string }>();
  const [modules, setModules] = useState<DungeonModule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!group) return;
    fetch("./data/json/dungeon_modules.json")
      .then<DungeonModule[]>((r) => r.json())
      .then((mods) => {
        const filtered = mods.filter((m) => m.group === group);
        filtered.sort((a, b) => {
          const sy = (a.size_y || 1) - (b.size_y || 1);
          if (sy !== 0) return sy;
          return (a.size_x || 1) - (b.size_x || 1);
        });
        setModules(filtered);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [group]);

  if (loading) return <div style={{ textAlign: "center", color: "#aaa", marginTop: 100 }}>加载中...</div>;
  if (!modules.length) return <div style={{ textAlign: "center", color: "#ff6b6b", marginTop: 100 }}>未找到</div>;

  const groupLabel = GROUP_LABELS[group || ""] || group || "未分组";

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Helmet>
        <title>{groupLabel} 地图模块 | DarkFindV5游戏导航</title>
        <meta name="description" content="{groupLabel} 地图模块，共 {modules.length} 个模块。" />
      </Helmet>
      <h1 style={{ textAlign: "center", color: "#00bcd4", fontSize: 28, margin: "0 0 8px" }}>
        【{groupLabel}】地图模块
        <span style={{ color: "#aaa", fontSize: 14, marginLeft: 12 }}>{modules.length} 个模块</span>
      </h1>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8,
      }}>
        {modules.map((mod) => {
          const sx = mod.size_x || 1;
          const sy = mod.size_y || 1;
          return (
            <Link
              key={mod.name}
              to={`/dungeon_modules/${group}/${mod.name}`}
              style={{ textDecoration: "none", minWidth: 0, gridColumn: sx >= 2 ? `span ${sx}` : undefined, gridRow: sy >= 2 ? `span ${sy}` : undefined }}
            >
              <div style={{
                background: "#3a3a3a",
                border: "1px solid #555",
                borderRadius: 5,
                padding: 8,
                cursor: "pointer",
                transition: "transform 0.2s, box-shadow 0.2s",
                height: "100%",
              }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-3px)";
                  e.currentTarget.style.boxShadow = "0 6px 16px rgba(0,0,0,0.4)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "none";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                <h3 style={{
                  margin: "0 0 2px 0", fontSize: 20, color: "#00bcd4",
                  textAlign: "center", width: "100%", lineHeight: 1.3,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {mod.translation || mod.name}
                </h3>
                <div style={{
                  fontSize: 12, color: "#888", textAlign: "center", marginBottom: 4,
                }}>
                  {sx}x{sy}
                </div>
                <div style={{
                  aspectRatio: `${sx} / ${sy}`,
                  background: "#2c2c2c",
                  border: "1px solid #666",
                  borderRadius: 4,
                  position: "relative",
                  overflow: "hidden",
                  backgroundImage: `url(./data/img/${mod.img_name || mod.sl_base_name || 'RareModule_1x1'}.webp)`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }} />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
