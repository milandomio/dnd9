import { useLocation, useNavigate } from "react-router-dom";
import { Switch } from "antd";
import { BulbOutlined } from "@ant-design/icons";
import { useTheme } from "../hooks/useTheme";
import { useDebug } from "../hooks/useDebug";

export default function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { dark, tokens, toggle } = useTheme();
  const { debug, toggle: toggleDebug } = useDebug();

  const isDetail = location.pathname.split("/").filter(Boolean).length >= 2;

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

  const debugBtnStyle = {
    ...linkStyle,
    background: debug ? "#4CAF50" : "#FFC107",
    color: debug ? "#fff" : "#000",
    border: debug ? "2px solid #388E3C" : "2px solid #FF9800",
    borderRadius: 6,
    fontSize: 13,
  };

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
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <a onClick={() => navigate("/")} style={linkStyle}
            onMouseEnter={(e) => { e.currentTarget.style.background = tokens.accent; e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = tokens.accent; }}
          >返回首页</a>
        {isDetail && (
          <a onClick={toggleDebug} style={debugBtnStyle}
            onMouseEnter={(e) => { if(!debug) { e.currentTarget.style.background = "#FF9800"; e.currentTarget.style.color = "#fff"; } }}
            onMouseLeave={(e) => { e.currentTarget.style.background = (debug ? "#4CAF50" : "#FFC107"); e.currentTarget.style.color = (debug ? "#fff" : "#000"); }}
          >{debug ? "退出调试" : "显示调试信息"}</a>
        )}
      </div>
    </div>
  );
}
