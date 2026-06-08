import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Spin, Typography, Tag } from "antd";
import type { ItemEntity, MonsterEntity, PropsEntity, Coord, DungeonModule } from "../types/data";

type Entity = ItemEntity | MonsterEntity | PropsEntity;

function zColor(z: number): string {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff4444";
}

export default function DetailPage() {
  const { page, name } = useParams<{ page: string; name: string }>();
  const [entity, setEntity] = useState<Entity | null>(null);
  const [modules, setModules] = useState<Map<string, DungeonModule>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!page || !name) return;
    Promise.all([
      fetch(`./data/${page}.json`).then<Entity[]>((r) => r.json()),
      fetch(`./data/dungeon_modules.json`).then<DungeonModule[]>((r) => r.json()),
    ])
      .then(([entities, mods]) => {
        const found = entities.find((e) => e.name === decodeURIComponent(name!));
        setEntity(found ?? null);
        setModules(new Map(mods.map((m) => [m.sl_base_name, m])));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, name]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!entity) return <Typography.Text type="danger">未找到</Typography.Text>;

  const coords = entity.coords;
  const grouped = new Map<string, Coord[]>();
  for (const c of coords) {
    if (!grouped.has(c.map)) grouped.set(c.map, []);
    grouped.get(c.map)!.push(c);
  }

  const sorted = [...grouped.entries()].sort((a, b) => {
    const ma = modules.get(a[0]);
    const mb = modules.get(b[0]);
    const sx_a = ma?.size_x ?? 1;
    const sy_a = ma?.size_y ?? 1;
    const sx_b = mb?.size_x ?? 1;
    const sy_b = mb?.size_y ?? 1;
    return sy_a - sy_b || sx_a - sx_b;
  });

  return (
    <div>
      <Typography.Title level={4}>
        {entity.translation || entity.name}
        <Typography.Text code style={{ fontSize: 14, marginLeft: 12 }}>
          {entity.name}
        </Typography.Text>
      </Typography.Title>

      {"monsters" in entity && entity.monsters && entity.monsters.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Typography.Text strong>掉落来源：</Typography.Text>
          {entity.monsters.map((m) => (
            <Tag key={m} style={{ marginTop: 4 }}>{m}</Tag>
          ))}
        </div>
      )}

      <Typography.Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        共 {coords.length} 个坐标，分布在 {grouped.size} 个模块
      </Typography.Text>

      <div style={{ marginBottom: 12, display: "flex", gap: 16, fontSize: 12 }}>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#00ffff", marginRight: 4 }}></span> Z &gt; 299 (高于地面)</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#ffff00", marginRight: 4 }}></span> -299 ≤ Z ≤ 299 (正常高度)</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#ff4444", marginRight: 4 }}></span> Z &lt; -299 (低于地面)</span>
      </div>

      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(4, 1fr)" }}>
        {sorted.map(([mapName, mapCoords]) => {
          const mod = modules.get(mapName);
          const sx = mod?.size_x ?? 1;
          const sy = mod?.size_y ?? 1;
          const cardStyle: React.CSSProperties = {
            gridColumn: sx >= 2 ? `span ${sx}` : undefined,
            aspectRatio: `${sx} / ${sy}`,
            background: "#141414",
            border: "1px solid #333",
            borderRadius: 8,
            padding: 12,
            position: "relative",
            overflow: "hidden",
          };
          if (mod?.sl_base_name) {
            cardStyle.backgroundImage = `url(./data/img/${mod.sl_base_name}.webp)`;
            cardStyle.backgroundSize = "cover";
            cardStyle.backgroundPosition = "center";
          }
          const range = Math.max(sx, sy) * 1600;
          return (
            <div key={mapName} style={cardStyle}>
              <div style={{
                background: "rgba(0,0,0,0.6)",
                padding: "4px 8px",
                borderRadius: 4,
                fontSize: 12,
                marginBottom: 4,
                display: "inline-block",
              }}>
                {mod?.translation || mapName}
              </div>
              {mapCoords.map((c, i) => {
                const px = ((c.x + range) / (range * 2)) * 100;
                const py = ((-c.y + range) / (range * 2)) * 100;
                const col = zColor(c.z);
                return (
                  <div key={i} style={{
                    position: "absolute",
                    left: `${px}%`,
                    top: `${py}%`,
                    transform: "translate(-50%, -50%)",
                    pointerEvents: "none",
                  }}>
                    <div style={{
                      width: 9,
                      height: 9,
                      borderRadius: "50%",
                      background: col,
                      boxShadow: `0 0 6px ${col}`,
                      border: "1px solid #fff",
                    }} />
                    <span style={{
                      position: "absolute",
                      left: "50%",
                      top: "100%",
                      transform: "translateX(-50%)",
                      fontSize: 11,
                      color: col,
                      whiteSpace: "nowrap",
                      textShadow: "0 0 4px #fff, 0 0 2px #000",
                      lineHeight: 1,
                      marginTop: 1,
                    }}>
                      {Math.round(c.z)}
                    </span>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
