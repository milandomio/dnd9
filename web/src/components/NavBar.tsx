import { useLocation, useNavigate } from "react-router-dom";
import { Switch } from "antd";
import { BulbOutlined } from "@ant-design/icons";
import { useTheme } from "../hooks/useTheme";

const LABEL_MAP: Record<string, string> = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
  lootdrops: "掉落表",
  dungeon_modules: "模块表",
};

export default function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const parts = location.pathname.split("/").filter(Boolean);
  const { dark, tokens, toggle } = useTheme();

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

  return (
    <div style={{
      display: "flex",
      justifyContent: "flex-end",
      alignItems: "center",
      gap: 8,
      maxWidth: 1200,
      margin: "0 auto 15px",
      padding: "8px 20px",
      background: tokens.surface,
      borderRadius: 5,
    }}>
      <div style={{ marginRight: "auto", display: "flex", alignItems: "center", gap: 6 }}>
        <BulbOutlined style={{ color: dark ? "#ffd700" : "#333", fontSize: 16 }} />
        <Switch checked={!dark} onChange={toggle} size="small" />
      </div>
      {parts.length > 0 && (
        <a onClick={() => navigate("/")} style={linkStyle}
          onMouseEnter={(e) => { e.currentTarget.style.background = tokens.accent; e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = tokens.accent; }}
        >返回首页</a>
      )}
      {parts.map((part, i) => {
        const label = LABEL_MAP[part] || decodeURIComponent(part);
        const path = "/" + parts.slice(0, i + 1).join("/");
        return (
          <span key={i}>
            {i > 0 && <span style={{ color: tokens.muted, margin: "0 4px" }}>&gt;</span>}
            <a onClick={() => navigate(path)} style={linkStyle}
              onMouseEnter={(e) => { e.currentTarget.style.background = tokens.accent; e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = tokens.accent; }}
            >{label}</a>
          </span>
        );
      })}
    </div>
  );
}
