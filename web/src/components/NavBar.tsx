import { useLocation, useNavigate } from "react-router-dom";
import { Switch } from "antd";
import { BulbOutlined } from "@ant-design/icons";
import { useTheme } from "../hooks/useTheme";

const LABEL_MAP: Record<string, string> = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
  lootdrops: "掉落表",
  explore: "探索地点表",
  quest_items: "任务物品表",
  quest_npc: "任务NPC表",
};

export default function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { dark, tokens, toggle } = useTheme();
  const parts = location.pathname.split("/").filter(Boolean);

  const linkStyle = {
    color: tokens.accent,
    textDecoration: "none" as const,
    fontSize: 15,
    fontWeight: "bold" as const,
    padding: "6px 16px",
    border: `1px solid ${tokens.accent}`,
    borderRadius: 5,
    cursor: "pointer" as const,
    transition: "all 0.2s",
  };

  const listPart = parts[0] ? { label: LABEL_MAP[parts[0]] || parts[0], path: "/" + parts[0] } : null;

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-end",
      gap: 8,
      maxWidth: 1200,
      margin: "0 auto 15px",
      padding: "8px 20px",
      background: tokens.surface,
      borderRadius: 5,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <BulbOutlined style={{ color: dark ? "#ffd700" : "#333", fontSize: 16 }} />
        <Switch checked={!dark} onChange={toggle} size="small" />
      </div>
      {listPart && parts.length >= 2 && (
        <a onClick={() => navigate(listPart.path)} style={linkStyle}
            onMouseEnter={(e) => { e.currentTarget.style.background = tokens.accent; e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = tokens.accent; }}
          >{listPart.label}</a>
      )}
      <a onClick={() => navigate("/")} style={linkStyle}
          onMouseEnter={(e) => { e.currentTarget.style.background = tokens.accent; e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = tokens.accent; }}
        >返回首页</a>
    </div>
  );
}
