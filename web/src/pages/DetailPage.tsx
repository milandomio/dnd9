import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Spin, Typography, Tag } from "antd";
import type { ItemEntity, MonsterEntity, PropsEntity, Coord, DungeonModule } from "../types/data";

type Entity = ItemEntity | MonsterEntity | PropsEntity;

function zColor(z: number): string {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff3333";
}

const GLOW = "0 0 4px #fff, 0 0 2px #000";

export default function DetailPage() {
  const { page, name } = useParams<{ page: string; name: string }>();
  const [entity, setEntity] = useState<Entity | null>(null);
  const [modules, setModules] = useState<Map<string, DungeonModule>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!page || !name) return;
    const decoded = decodeURIComponent(name!);
    Promise.all([
      fetch(`./data/${page}/${decoded}.json`).then<Entity>((r) => r.json()),
      fetch(`./data/dungeon_modules.json`).then<DungeonModule[]>((r) => r.json()),
    ])
      .then(([entity, mods]) => {
        setEntity(entity);
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
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
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
          const range = Math.max(sx, sy) * 1600;
          return (
            <div key={mapName} style={{
              minWidth: 0,
              gridColumn: sx >= 2 ? `span ${sx}` : undefined,
              gridRow: sy >= 2 ? `span ${sy}` : undefined,
              background: "#3a3a3a",
              border: "1px solid #555",
              borderRadius: 5,
              padding: 8,
            }}>
              <h3 style={{
                margin: "0 0 6px 0",
                fontSize: 14,
                color: "#00bcd4",
                textAlign: "center",
                width: "100%",
                lineHeight: 1.3,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}>
                {mod?.translation || mapName}
              </h3>
              <div style={{
                aspectRatio: `${sx} / ${sy}`,
                background: "#2c2c2c",
                border: "1px solid #666",
                borderRadius: 4,
                position: "relative",
                overflow: "hidden",
                ...(mod?.sl_base_name ? {
                  backgroundImage: `url(./data/img/${mod.sl_base_name}.webp)`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                } : {}),
              }}>
                {mapCoords.map((c, i) => {
                  let x = c.x + (mod?.offset_x ?? 0);
                  let y = c.y + (mod?.offset_y ?? 0);
                  const r = mod?.rotate ?? 0;
                  if (r === 1) { const nx = y; const ny = -x; x = nx; y = ny; }
                  else if (r === 2) { x = -x; y = -y; }
                  else if (r === 3) { const nx = -y; const ny = x; x = nx; y = ny; }
                  const multX = sx === 1 && sy === 2 ? 100 : 50;
                  const centerX = sx === 1 && sy === 2 ? 100 : 50;
                  const multY = 50;
                  const centerY = 50;
                  const px = centerX + (x / range) * multX;
                  const py = centerY + (y / range) * multY;
                  const col = zColor(c.z);
                  const textCol = col === "#ff3333" ? "#ffffff" : col;
                  const textShadow = col === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW;
                  return (
                    <div key={i} style={{
                      position: "absolute",
                      left: `${px}%`,
                      top: `${py}%`,
                      width: 9,
                      height: 9,
                      borderRadius: "50%",
                      background: col,
                      boxShadow: `0 0 6px ${col}`,
                      border: "1px solid #fff",
                      transform: "translate(-50%, -50%)",
                      zIndex: 10,
                    }}>
                      <span style={{
                        position: "absolute",
                        left: "50%",
                        top: "100%",
                        transform: "translateX(-50%)",
                        fontSize: 11,
                        fontFamily: "Arial, sans-serif",
                        color: textCol,
                        whiteSpace: "nowrap",
                        textShadow: textShadow,
                        lineHeight: 1,
                        marginTop: 1,
                      }}>
                        {Math.round(c.z)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
