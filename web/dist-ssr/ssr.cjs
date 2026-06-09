"use strict";
Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
const jsxRuntime = require("react/jsx-runtime");
const server = require("react-dom/server");
const server_mjs = require("react-router-dom/server.mjs");
const reactHelmetAsync = require("react-helmet-async");
const antd = require("antd");
const zhCN = require("antd/locale/zh_CN.js");
const react = require("react");
const reactRouterDom = require("react-router-dom");
const icons = require("@ant-design/icons");
const LIGHT = {
  bg: "#f5f5f5",
  surface: "#e0e0e0",
  card: "#d0d0d0",
  text: "#1a1a1a",
  muted: "#666",
  border: "#bbb",
  accent: "#0097a7"
};
const DARK = {
  bg: "#2c2c2c",
  surface: "#3a3a3a",
  card: "#444",
  text: "#ffffff",
  muted: "#aaa",
  border: "#555",
  accent: "#00bcd4"
};
const ThemeCtx = react.createContext({ dark: true, tokens: DARK, toggle: () => {
} });
function ThemeProvider({ children }) {
  const [dark, setDark] = react.useState(true);
  const toggle = () => setDark((v) => !v);
  const tokens = dark ? DARK : LIGHT;
  react.useEffect(() => {
    const bg = dark ? "#2c2c2c" : "#f5f5f5";
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    document.documentElement.style.background = bg;
    document.body.style.background = bg;
    document.body.style.margin = "0";
  }, [dark]);
  return /* @__PURE__ */ jsxRuntime.jsx(ThemeCtx.Provider, { value: { dark, tokens, toggle }, children });
}
function useTheme() {
  return react.useContext(ThemeCtx);
}
const DebugContext = react.createContext(null);
function DebugProvider({ children }) {
  const [debug, setDebug] = react.useState(false);
  const [adjOffsets, setAdjOffsets] = react.useState({});
  const toggle = react.useCallback(() => setDebug((d) => !d), []);
  return /* @__PURE__ */ jsxRuntime.jsx(DebugContext.Provider, { value: { debug, toggle, adjOffsets, setAdjOffsets }, children });
}
function useDebug() {
  const ctx = react.useContext(DebugContext);
  if (!ctx) throw new Error("useDebug must be used within DebugProvider");
  return ctx;
}
const SSRDataContext = react.createContext(null);
function useSSRData(key) {
  const ctx = react.useContext(SSRDataContext);
  if (ctx) return ctx[key] ?? null;
  if (typeof window !== "undefined") {
    const w = window;
    if (w.__SSR_DATA__ && w.__SSR_DATA__[key]) return w.__SSR_DATA__[key];
  }
  return null;
}
const box = {
  textAlign: "center",
  color: "#ff6b6b",
  fontSize: 14,
  marginBottom: 20,
  padding: 8,
  background: "#3a3a3a",
  borderRadius: 5,
  maxWidth: 700,
  marginLeft: "auto",
  marginRight: "auto"
};
function Disclaimer() {
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: box, children: [
    "⚠️ 数据有误差，以实际游戏内为准",
    /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#aaa", marginLeft: 15 }, children: [
      "地图生成日期：2026-06-08",
      /* @__PURE__ */ jsxRuntime.jsx("span", { style: { fontSize: 10 }, children: " 地图页面设计-雪鸡Official" })
    ] })
  ] });
}
const CARD_THEME = {
  items: { border: "#4CAF50", hoverBg: "linear-gradient(145deg, #2a4a2a, #3a5a3a)", icon: "📦", titleColor: "#fff" },
  monsters: { border: "#FF6600", hoverBg: "linear-gradient(145deg, #4a3a2a, #5a4a3a)", icon: "👹", titleColor: "#fff" },
  props: { border: "#9C27B0", hoverBg: "linear-gradient(145deg, #3a2a4a, #4a3a5a)", icon: "🏛️", titleColor: "#CE93D8" },
  lootdrops: { border: "#2196F3", hoverBg: "linear-gradient(145deg, #2a3a4a, #3a4a5a)", icon: "💎", titleColor: "#fff" },
  explore: { border: "#00bcd4", hoverBg: "linear-gradient(145deg, #2a4a4a, #3a5a5a)", icon: "🗺️", titleColor: "#00bcd4" },
  quest_items: { border: "#E91E63", hoverBg: "linear-gradient(145deg, #4a2a3a, #5a3a4a)", icon: "📋", titleColor: "#F06292" },
  quest_npc: { border: "#FFC107", hoverBg: "linear-gradient(145deg, #4a4a2a, #5a5a3a)", icon: "🗡️", titleColor: "#FFD54F" }
};
const DEFAULT_THEME = { border: "#555", hoverBg: "linear-gradient(145deg, #3a3a3a, #444)", icon: "📄", titleColor: "#fff" };
function HomePage() {
  const ssrData = useSSRData("home");
  const [data, setData] = react.useState(ssrData || []);
  const [loading, setLoading] = react.useState(!ssrData);
  const navigate = reactRouterDom.useNavigate();
  react.useEffect(() => {
    if (ssrData) return;
    fetch("./data/json/index.json").then((r) => r.json()).then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsx("title", { children: "DarkFindV5游戏导航 | 道具、怪物、物品、掉落位置查询" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "DarkFindV5 游戏导航——查询游戏内物品、怪物、实体、掉落物的地图位置，支持坐标偏移调试。" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:title", content: "DarkFindV5游戏导航" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:description", content: "查询游戏内物品、怪物、实体、掉落物的地图位置" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:type", content: "website" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }, children: "DarkFindV5游戏导航" }),
    /* @__PURE__ */ jsxRuntime.jsx(Disclaimer, {}),
    /* @__PURE__ */ jsxRuntime.jsx("div", { style: {
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 20
    }, children: data.map((entry) => {
      const t = CARD_THEME[entry.page] ?? DEFAULT_THEME;
      return /* @__PURE__ */ jsxRuntime.jsxs(
        "div",
        {
          onClick: () => navigate(`/${entry.page}`),
          style: {
            background: "linear-gradient(145deg, #3a3a3a, #444444)",
            border: `2px solid ${t.border}`,
            borderRadius: 16,
            padding: "30px 20px",
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
          },
          onMouseEnter: (e) => {
            e.currentTarget.style.background = t.hoverBg;
            e.currentTarget.style.transform = "translateY(-8px) scale(1.02)";
            e.currentTarget.style.boxShadow = "0 12px 24px rgba(0,0,0,0.5)";
          },
          onMouseLeave: (e) => {
            e.currentTarget.style.background = "linear-gradient(145deg, #3a3a3a, #444444)";
            e.currentTarget.style.transform = "none";
            e.currentTarget.style.boxShadow = "0 4px 6px rgba(0,0,0,0.3)";
          },
          children: [
            /* @__PURE__ */ jsxRuntime.jsx("div", { style: { fontSize: 48, marginBottom: 8, filter: `drop-shadow(0 0 8px ${t.border})` }, children: t.icon }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#fff", fontSize: 24, fontWeight: "bold", marginBottom: 4 }, children: [
              "【",
              entry.label,
              "】"
            ] }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: t.titleColor, fontSize: 14 }, children: [
              entry.label,
              entry.count,
              "个"
            ] }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#888", fontSize: 14, marginTop: 4 }, children: [
              entry.page === "items" && "查看物品位置",
              entry.page === "monsters" && "查看怪物位置",
              entry.page === "props" && "查看实体位置",
              entry.page === "lootdrops" && "查看物品掉落怪物",
              entry.page === "explore" && "地图模块预览",
              entry.page === "quest_items" && "按地图分组查看任务物品",
              entry.page === "quest_npc" && "查看NPC任务详情"
            ] })
          ]
        },
        entry.page
      );
    }) })
  ] });
}
const LABEL_MAP$1 = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
  lootdrops: "掉落表"
};
function ListPage() {
  const { page } = reactRouterDom.useParams();
  const navigate = reactRouterDom.useNavigate();
  const ssrData = useSSRData(`list-${page}`);
  const [data, setData] = react.useState(ssrData || []);
  const [loading, setLoading] = react.useState(!ssrData);
  const [debug, setDebug] = react.useState(false);
  react.useEffect(() => {
    if (!page || !["items", "monsters", "props", "lootdrops"].includes(page)) return;
    if (ssrData) return;
    fetch(`./data/json/${page}.json`).then((r) => r.json()).then(setData).catch(console.error).finally(() => setLoading(false));
  }, [page]);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsxs("title", { children: [
        "【",
        LABEL_MAP$1[page] ?? page,
        "】实体位置汇总 | DarkFindV5游戏导航"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "{LABEL_MAP[page!] ?? page} 共 {data.length} 个实体，查询地图位置分布。" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:title", content: "【{LABEL_MAP[page!] ?? page}】实体位置汇总" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:description", content: "共 {data.length} 个实体" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsxs("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }, children: [
      "【",
      LABEL_MAP$1[page] ?? page,
      "】实体位置汇总"
    ] }),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }, children: [
      "有效实体",
      data.length,
      "个"
    ] }),
    debug && /* @__PURE__ */ jsxRuntime.jsx(
      "button",
      {
        onClick: () => setDebug(false),
        style: {
          position: "fixed",
          top: 20,
          right: 20,
          padding: "10px 20px",
          background: "#4CAF50",
          color: "#fff",
          border: "2px solid #388E3C",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: 14,
          fontWeight: "bold",
          zIndex: 9999,
          boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
        },
        children: "退出调试"
      }
    ),
    !debug && /* @__PURE__ */ jsxRuntime.jsx(
      "button",
      {
        onClick: () => setDebug(true),
        style: {
          position: "fixed",
          top: 20,
          right: 20,
          padding: "10px 20px",
          background: "#FFC107",
          color: "#000",
          border: "2px solid #FF9800",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: 14,
          fontWeight: "bold",
          zIndex: 9999,
          boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
        },
        children: "显示全部"
      }
    ),
    /* @__PURE__ */ jsxRuntime.jsx("div", { className: "section-content", style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 20
    }, children: data.map((entity) => {
      var _a;
      return /* @__PURE__ */ jsxRuntime.jsxs(
        "div",
        {
          onClick: () => {
            if (page === "lootdrops") {
              navigate(`/lootdrops/${entity.name}`);
            } else {
              navigate(`/${page}/${entity.name}`);
            }
          },
          style: {
            background: "#3a3a3a",
            border: "1px solid #555",
            borderRadius: 8,
            padding: 20,
            textAlign: "center",
            cursor: "pointer",
            transition: "transform 0.2s, box-shadow 0.2s"
          },
          onMouseEnter: (e) => {
            e.currentTarget.style.transform = "translateY(-5px)";
            e.currentTarget.style.boxShadow = "0 5px 15px rgba(0,0,0,0.5)";
          },
          onMouseLeave: (e) => {
            e.currentTarget.style.transform = "none";
            e.currentTarget.style.boxShadow = "none";
          },
          children: [
            /* @__PURE__ */ jsxRuntime.jsx("div", { style: { color: "#fff", fontSize: 18, fontWeight: "bold" }, children: entity.translation || entity.name }),
            debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#888", fontSize: 12, marginTop: 4 }, children: [
              entity.translation,
              "【",
              entity.name,
              "】"
            ] }),
            entity.monsters && entity.monsters.length > 0 && page === "lootdrops" && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#ccc", fontSize: 13, marginTop: 6, lineHeight: 1.5 }, children: [
              entity.variant_count && entity.variant_count > 1 ? /* @__PURE__ */ jsxRuntime.jsxs(jsxRuntime.Fragment, { children: [
                " [",
                entity.variant_count,
                "变体] -目标- "
              ] }) : /* @__PURE__ */ jsxRuntime.jsx(jsxRuntime.Fragment, { children: " -目标- " }),
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#aaa" }, children: entity.monster_translations && entity.monster_translations.length <= 6 ? entity.monster_translations.join("、") : ((_a = entity.monster_translations) == null ? void 0 : _a.slice(0, 5).join("、")) + "..." })
            ] }),
            entity.monsters && entity.monsters.length > 0 && page !== "lootdrops" && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#aaa", fontSize: 13, marginTop: 6 }, children: [
              "掉落来源: ",
              entity.monsters.length,
              "个"
            ] })
          ]
        },
        entity.name
      );
    }) })
  ] });
}
const ctrlBtn = {
  background: "#555",
  color: "#ccc",
  border: "1px solid #777",
  borderRadius: 3,
  padding: "1px 6px",
  cursor: "pointer",
  fontSize: 11
};
const ctrlInput = {
  width: 55,
  background: "#333",
  color: "#fff",
  border: "1px solid #666",
  borderRadius: 3,
  padding: "1px 4px",
  fontSize: 11,
  textAlign: "center"
};
function getAdj(mapName, modRotate, adjOffsets) {
  const a = adjOffsets[mapName];
  return {
    x: (a == null ? void 0 : a.x) ?? 0,
    y: (a == null ? void 0 : a.y) ?? 0,
    range: (a == null ? void 0 : a.range) ?? 0,
    rotate: (a == null ? void 0 : a.rotate) ?? modRotate ?? 1,
    mirrorX: (a == null ? void 0 : a.mirrorX) ?? false,
    mirrorY: (a == null ? void 0 : a.mirrorY) ?? false
  };
}
function applyTransform(ox, oy, offX, offY, adj) {
  let x = ox;
  let y = oy;
  const r = adj.rotate;
  if (r === 1) {
    const nx = y;
    const ny = -x;
    x = nx;
    y = ny;
  } else if (r === 2) {
    x = -x;
    y = -y;
  } else if (r === 3) {
    const nx = -y;
    const ny = x;
    x = nx;
    y = ny;
  }
  if (adj.mirrorX) x = -x;
  if (adj.mirrorY) y = -y;
  x += offX;
  y += offY;
  return [x, y];
}
function computePixel(x, y, range, sx, sy) {
  const multX = sx === 1 && sy === 2 ? 100 : 50;
  const centerX = sx === 1 && sy === 2 ? 100 : 50;
  const multY = 50;
  const centerY = 50;
  return [
    centerX + x / (range || 1600) * multX,
    centerY + y / (range || 1600) * multY
  ];
}
const th = { padding: "4px 6px", borderBottom: "1px solid #555", textAlign: "center", verticalAlign: "middle" };
const td = { padding: "3px 6px", borderBottom: "1px solid #555", textAlign: "center", alignContent: "center" };
const checkTd = { ...td, width: 24, textAlign: "center", verticalAlign: "middle" };
const checkboxStyle = { accentColor: "#00bcd4", cursor: "pointer", margin: 0 };
const labelStyle = { cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, userSelect: "none" };
function HdrChk({ checked, onChange, label }) {
  return /* @__PURE__ */ jsxRuntime.jsxs("label", { style: labelStyle, children: [
    /* @__PURE__ */ jsxRuntime.jsx("input", { type: "checkbox", checked, onChange, style: checkboxStyle }),
    label
  ] });
}
function DebugCoordTable({ rows, onToggleRow, onToggleGroup, onToggleFile, onToggleMap, onToggleLabel, showMonster }) {
  const allVisible = (pred) => {
    const matched = rows.filter(pred);
    return matched.length > 0 && matched.every((r) => !r.hidden);
  };
  const allRowsHidden = rows.length > 0 && rows.every((r) => r.hidden);
  function colToggle(pred) {
    const matched = rows.filter(pred);
    if (matched.length === 0) return;
    const hideAll = matched.some((r) => !r.hidden);
    for (const r of matched) {
      if (hideAll && !r.hidden) onToggleRow(r.key);
      else if (!hideAll && r.hidden) onToggleRow(r.key);
    }
  }
  function CellChk({ visible, onToggle }) {
    return /* @__PURE__ */ jsxRuntime.jsx("input", { type: "checkbox", checked: visible, onChange: onToggle, style: checkboxStyle });
  }
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { marginTop: 12, background: "#3a3a3a", borderRadius: 5, padding: 10, overflowX: "auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsx("h3", { style: { textAlign: "center", color: "#00bcd4", fontSize: 18, margin: "0 0 10px" }, children: "所有坐标详情" }),
    /* @__PURE__ */ jsxRuntime.jsxs("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13, color: "#aaa" }, children: [
      /* @__PURE__ */ jsxRuntime.jsx("thead", { children: /* @__PURE__ */ jsxRuntime.jsxs("tr", { style: { background: "#555", fontWeight: "bold" }, children: [
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: checkTd, children: /* @__PURE__ */ jsxRuntime.jsx(
          "input",
          {
            type: "checkbox",
            checked: !allRowsHidden,
            onChange: () => colToggle(() => true),
            style: checkboxStyle
          }
        ) }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: onToggleGroup ? /* @__PURE__ */ jsxRuntime.jsx(HdrChk, { checked: allVisible(() => true), onChange: () => colToggle(() => true), label: "分组" }) : "分组" }),
        showMonster && /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: onToggleLabel ? /* @__PURE__ */ jsxRuntime.jsx(HdrChk, { checked: allVisible(() => true), onChange: () => colToggle(() => true), label: "怪物" }) : "怪物" }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: onToggleFile ? /* @__PURE__ */ jsxRuntime.jsx(HdrChk, { checked: allVisible(() => true), onChange: () => colToggle(() => true), label: "地图文件" }) : "地图文件" }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: onToggleMap ? /* @__PURE__ */ jsxRuntime.jsx(HdrChk, { checked: allVisible(() => true), onChange: () => colToggle(() => true), label: "地图" }) : "地图" }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: onToggleLabel ? /* @__PURE__ */ jsxRuntime.jsx(HdrChk, { checked: allVisible(() => true), onChange: () => colToggle(() => true), label: "标签" }) : "标签" }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: "X" }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: "Y" }),
        /* @__PURE__ */ jsxRuntime.jsx("th", { style: th, children: "Z" })
      ] }) }),
      /* @__PURE__ */ jsxRuntime.jsx("tbody", { children: rows.map((row, idx) => {
        const isHidden = row.hidden;
        return /* @__PURE__ */ jsxRuntime.jsxs("tr", { style: {
          background: isHidden ? "#2a2a2a" : idx % 2 === 0 ? "#333" : "#3a3a3a",
          opacity: isHidden ? 0.35 : 1,
          textDecoration: isHidden ? "line-through" : "none"
        }, children: [
          /* @__PURE__ */ jsxRuntime.jsx("td", { style: checkTd, children: /* @__PURE__ */ jsxRuntime.jsx(
            "input",
            {
              type: "checkbox",
              checked: !isHidden,
              onChange: () => onToggleRow(row.key),
              style: checkboxStyle
            }
          ) }),
          /* @__PURE__ */ jsxRuntime.jsx(
            "td",
            {
              style: { ...td, cursor: "pointer" },
              onClick: () => onToggleGroup == null ? void 0 : onToggleGroup(row.groupKey ?? row.group),
              children: /* @__PURE__ */ jsxRuntime.jsxs("label", { style: labelStyle, onClick: (e) => e.stopPropagation(), children: [
                /* @__PURE__ */ jsxRuntime.jsx(
                  CellChk,
                  {
                    visible: allVisible((r) => (r.groupKey ?? r.group) === (row.groupKey ?? row.group)),
                    onToggle: () => onToggleGroup == null ? void 0 : onToggleGroup(row.groupKey ?? row.group)
                  }
                ),
                row.group
              ] })
            }
          ),
          showMonster && row.monster && /* @__PURE__ */ jsxRuntime.jsx("td", { style: { ...td, cursor: "pointer" }, onClick: () => {
            var _a, _b;
            return (_b = (_a = row.monster) == null ? void 0 : _a.onToggle) == null ? void 0 : _b.call(_a);
          }, children: /* @__PURE__ */ jsxRuntime.jsxs("label", { style: labelStyle, onClick: (e) => e.stopPropagation(), children: [
            /* @__PURE__ */ jsxRuntime.jsx(
              CellChk,
              {
                visible: allVisible((r) => {
                  var _a, _b;
                  return ((_a = r.monster) == null ? void 0 : _a.name) === ((_b = row.monster) == null ? void 0 : _b.name);
                }),
                onToggle: () => {
                  var _a, _b;
                  return (_b = (_a = row.monster) == null ? void 0 : _a.onToggle) == null ? void 0 : _b.call(_a);
                }
              }
            ),
            /* @__PURE__ */ jsxRuntime.jsx("span", { style: { width: 8, height: 8, borderRadius: "50%", background: row.monster.color, display: "inline-block", flexShrink: 0 } }),
            row.monster.translation
          ] }) }),
          /* @__PURE__ */ jsxRuntime.jsx(
            "td",
            {
              style: { ...td, cursor: "pointer" },
              onClick: () => onToggleFile == null ? void 0 : onToggleFile(row.file),
              children: /* @__PURE__ */ jsxRuntime.jsxs("label", { style: labelStyle, onClick: (e) => e.stopPropagation(), children: [
                /* @__PURE__ */ jsxRuntime.jsx(
                  CellChk,
                  {
                    visible: allVisible((r) => r.file === row.file),
                    onToggle: () => onToggleFile == null ? void 0 : onToggleFile(row.file)
                  }
                ),
                row.file
              ] })
            }
          ),
          /* @__PURE__ */ jsxRuntime.jsx(
            "td",
            {
              style: { ...td, cursor: "pointer" },
              onClick: () => onToggleMap == null ? void 0 : onToggleMap(row.mapName),
              children: /* @__PURE__ */ jsxRuntime.jsxs("label", { style: labelStyle, onClick: (e) => e.stopPropagation(), children: [
                /* @__PURE__ */ jsxRuntime.jsx(
                  CellChk,
                  {
                    visible: allVisible((r) => r.mapName === row.mapName),
                    onToggle: () => onToggleMap == null ? void 0 : onToggleMap(row.mapName)
                  }
                ),
                row.mapLabel
              ] })
            }
          ),
          /* @__PURE__ */ jsxRuntime.jsx(
            "td",
            {
              style: { ...td, cursor: "pointer", fontSize: 11 },
              onClick: () => onToggleLabel == null ? void 0 : onToggleLabel(row.label),
              children: /* @__PURE__ */ jsxRuntime.jsxs("label", { style: labelStyle, onClick: (e) => e.stopPropagation(), children: [
                /* @__PURE__ */ jsxRuntime.jsx(
                  CellChk,
                  {
                    visible: allVisible((r) => r.label === row.label),
                    onToggle: () => onToggleLabel == null ? void 0 : onToggleLabel(row.label)
                  }
                ),
                row.label
              ] })
            }
          ),
          /* @__PURE__ */ jsxRuntime.jsx("td", { style: td, children: row.x.toFixed(2) }),
          /* @__PURE__ */ jsxRuntime.jsx("td", { style: td, children: row.y.toFixed(2) }),
          /* @__PURE__ */ jsxRuntime.jsx("td", { style: td, children: row.z.toFixed(2) })
        ] }, row.key);
      }) })
    ] })
  ] });
}
const GROUP_LABELS$1 = {
  Crypt: "废墟2层地牢",
  FireDeep: "哥布林洞穴2层",
  GoblinCave: "哥布林洞穴1层",
  IceAbyss: "冰图2层",
  IceCavern: "冰图1层",
  Inferno: "废墟3层炼狱",
  Ruins: "废墟1层",
  ShipGraveyard: "水图"
};
function zColor$1(z) {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff3333";
}
const GLOW$1 = "0 0 4px #fff, 0 0 2px #000";
function DetailPage() {
  const { page, name } = reactRouterDom.useParams();
  const dataKey = `${page}/${name ? decodeURIComponent(name) : ""}`;
  const ssrData = useSSRData(dataKey);
  const [entity, setEntity] = react.useState((ssrData == null ? void 0 : ssrData.entity) || null);
  const [modules, setModules] = react.useState(
    ssrData ? new Map(ssrData.modules.map((m) => [m.name, m])) : /* @__PURE__ */ new Map()
  );
  const [loading, setLoading] = react.useState(!ssrData);
  const [hiddenRows, setHiddenRows] = react.useState(/* @__PURE__ */ new Set());
  const { debug, toggle, adjOffsets, setAdjOffsets } = useDebug();
  const toggleRow = (key) => {
    setHiddenRows((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };
  function myGetAdj(mapName, mod) {
    return getAdj(mapName, mod == null ? void 0 : mod.rotate, adjOffsets);
  }
  function setAdj(mapName, field, value) {
    setAdjOffsets((prev) => {
      const cur = prev[mapName] || { x: 0, y: 0, range: 0, rotate: 0, mirrorX: false, mirrorY: false };
      return { ...prev, [mapName]: { ...cur, [field]: value } };
    });
  }
  react.useEffect(() => {
    if (!page || !name) return;
    if (ssrData) return;
    const decoded = decodeURIComponent(name);
    Promise.all([
      fetch(`./data/json/${page}/${decoded}.json`).then((r) => r.json()),
      fetch(`./data/json/dungeon_modules.json`).then((r) => r.json())
    ]).then(([entityData, mods]) => {
      setEntity(entityData);
      const mm = /* @__PURE__ */ new Map();
      mods.forEach((m) => {
        mm.set(m.name, m);
        mm.set(m.sl_base_name, m);
      });
      setModules(mm);
    }).catch(console.error).finally(() => setLoading(false));
  }, [page, name]);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  if (!entity) return /* @__PURE__ */ jsxRuntime.jsx(antd.Typography.Text, { type: "danger", children: "未找到" });
  const coords = entity.coords;
  const grouped = /* @__PURE__ */ new Map();
  for (const c of coords) {
    if (!grouped.has(c.map)) grouped.set(c.map, []);
    grouped.get(c.map).push(c);
  }
  const groupedByType = /* @__PURE__ */ new Map();
  for (const [mapName, mapCoords] of grouped) {
    const mod = modules.get(mapName);
    const g = (mod == null ? void 0 : mod.group) || "";
    if (!groupedByType.has(g)) groupedByType.set(g, []);
    groupedByType.get(g).push({ mapName, mod, coords: mapCoords });
  }
  for (const [_, items] of groupedByType) {
    items.sort((a, b) => {
      var _a, _b, _c, _d;
      const sy_a = ((_a = a.mod) == null ? void 0 : _a.size_y) ?? 1;
      const sy_b = ((_b = b.mod) == null ? void 0 : _b.size_y) ?? 1;
      const sx_a = ((_c = a.mod) == null ? void 0 : _c.size_x) ?? 1;
      const sx_b = ((_d = b.mod) == null ? void 0 : _d.size_x) ?? 1;
      return sy_a - sy_b || sx_a - sx_b;
    });
  }
  const groupOrder = Object.keys(GROUP_LABELS$1);
  const sortedGroups = [...groupedByType.entries()].sort(([a], [b]) => {
    return groupOrder.indexOf(a) - groupOrder.indexOf(b);
  });
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsxs("title", { children: [
        entity.translation || entity.name,
        " 位置汇总 | DarkFindV5游戏导航"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "{entity.translation || entity.name}（{entity.name}）在游戏内的地图位置分布，共 {coords.length} 个位置点。" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:title", content: "{entity.translation || entity.name} 位置汇总 | DarkFindV5" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:description", content: "{entity.translation || entity.name} 共 {coords.length} 个位置点" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsxs("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 36, margin: "0 0 12px" }, children: [
      entity.translation || entity.name,
      " 位置汇总"
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: toggle, style: {
      position: "fixed",
      top: 20,
      right: 20,
      padding: "4px 16px",
      background: debug ? "#4CAF50" : "#FFC107",
      color: debug ? "#fff" : "#000",
      border: debug ? "2px solid #388E3C" : "2px solid #FF9800",
      borderRadius: 6,
      cursor: "pointer",
      fontSize: 13,
      fontWeight: "bold",
      zIndex: 9999,
      boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
    }, children: debug ? "退出调试" : "显示调试信息" }),
    /* @__PURE__ */ jsxRuntime.jsx(Disclaimer, {}),
    /* @__PURE__ */ jsxRuntime.jsx("div", { style: { display: "grid", gap: 6, gridTemplateColumns: "repeat(4, 1fr)" }, children: sortedGroups.map(([groupName, items]) => /* @__PURE__ */ jsxRuntime.jsxs(jsxRuntime.Fragment, { children: [
      groupName && /* @__PURE__ */ jsxRuntime.jsx("div", { style: {
        gridColumn: "1 / -1",
        fontSize: 22,
        fontWeight: "bold",
        color: "#FFC107",
        padding: "5px 0",
        marginTop: 10,
        borderBottom: "2px solid #FFC107"
      }, children: GROUP_LABELS$1[groupName] || groupName }, `h-${groupName}`),
      items.map(({ mapName, mod, coords: mapCoords }) => {
        const sx = (mod == null ? void 0 : mod.size_x) ?? 1;
        const sy = (mod == null ? void 0 : mod.size_y) ?? 1;
        const baseRange = (mod == null ? void 0 : mod.range) || Math.max(sx, sy) * 1600;
        const adj = myGetAdj(mapName, mod);
        const range = baseRange + adj.range || 1600;
        const offX = ((mod == null ? void 0 : mod.offset_x) ?? 0) + adj.x;
        const offY = ((mod == null ? void 0 : mod.offset_y) ?? 0) + adj.y;
        return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
          minWidth: 0,
          gridColumn: sx >= 2 ? `span ${sx}` : void 0,
          gridRow: sy >= 2 ? `span ${sy}` : void 0,
          background: "#3a3a3a",
          border: "1px solid #555",
          borderRadius: 5,
          padding: 8
        }, children: [
          /* @__PURE__ */ jsxRuntime.jsxs("h3", { style: {
            margin: "0 0 6px 0",
            fontSize: 22,
            color: "#00bcd4",
            textAlign: "center",
            width: "100%",
            lineHeight: 1.3,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap"
          }, children: [
            (mod == null ? void 0 : mod.translation) || mapName,
            debug && /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#888", fontSize: 11 }, children: [
              " (",
              mapName,
              ")"
            ] })
          ] }),
          debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4 }, children: [
            (mod == null ? void 0 : mod.img_name) || (mod == null ? void 0 : mod.sl_base_name) || mapName,
            ".webp | 找到 ",
            mapCoords.length,
            " 个位置 | 范围: ±",
            range
          ] }),
          debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4, lineHeight: 1.4 }, children: [
            mapCoords[0].file,
            /* @__PURE__ */ jsxRuntime.jsx("br", {}),
            "旋转:",
            (mod == null ? void 0 : mod.rotate) ?? 0,
            " 偏移:(",
            (mod == null ? void 0 : mod.offset_x) ?? 0,
            ",",
            (mod == null ? void 0 : mod.offset_y) ?? 0,
            ") 大小:",
            sx,
            "x",
            sy
          ] }),
          /* @__PURE__ */ jsxRuntime.jsx("div", { style: {
            aspectRatio: `${sx} / ${sy}`,
            background: "#2c2c2c",
            border: "1px solid #666",
            borderRadius: 4,
            position: "relative",
            overflow: "hidden",
            backgroundImage: `url(./data/img/${(mod == null ? void 0 : mod.img_name) || (mod == null ? void 0 : mod.sl_base_name) || "RareModule_1x1"}.webp)`,
            backgroundSize: "cover",
            backgroundPosition: "center"
          }, children: mapCoords.map((c, i) => {
            const [x, y] = applyTransform(c.x, c.y, offX, offY, adj);
            const [px, py] = computePixel(x, y, range, sx, sy);
            const col = zColor$1(c.z);
            const textCol = col === "#ff3333" ? "#ffffff" : col;
            const textShadow = col === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW$1;
            return /* @__PURE__ */ jsxRuntime.jsx("div", { style: {
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
              zIndex: 10
            }, children: /* @__PURE__ */ jsxRuntime.jsx("span", { style: {
              position: "absolute",
              left: "50%",
              top: "100%",
              transform: "translateX(-50%)",
              fontSize: 11,
              fontFamily: "Arial, sans-serif",
              color: textCol,
              whiteSpace: "nowrap",
              textShadow,
              lineHeight: 1,
              marginTop: 1
            }, children: Math.round(c.z) }) }, i);
          }) }),
          debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { fontSize: 11, color: "#aaa", marginTop: 4, display: "flex", flexDirection: "column", gap: 3 }, children: [
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888" }, children: "范围:" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "range", Math.round(range / 2) - baseRange), style: ctrlBtn, children: "÷2" }),
              /* @__PURE__ */ jsxRuntime.jsx("input", { type: "number", value: range, onChange: (e) => setAdj(mapName, "range", Number(e.target.value) - baseRange), style: ctrlInput, step: 100 }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "range", range * 2 - baseRange), style: ctrlBtn, children: "x2" }),
              /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#aaa", fontSize: 12, marginLeft: 4 }, children: [
                "↻",
                adj.rotate
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888" }, children: "偏移:" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "y", adj.y - 50), style: ctrlBtn, children: "↑" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "y", adj.y + 50), style: ctrlBtn, children: "↓" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "x", adj.x - 50), style: ctrlBtn, children: "←" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "x", adj.x + 50), style: ctrlBtn, children: "→" }),
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888", marginLeft: 8 }, children: "X:" }),
              /* @__PURE__ */ jsxRuntime.jsx("input", { type: "number", value: offX, onChange: (e) => setAdj(mapName, "x", Number(e.target.value) - ((mod == null ? void 0 : mod.offset_x) ?? 0)), style: ctrlInput, step: 10 }),
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888" }, children: "Y:" }),
              /* @__PURE__ */ jsxRuntime.jsx("input", { type: "number", value: offY, onChange: (e) => setAdj(mapName, "y", Number(e.target.value) - ((mod == null ? void 0 : mod.offset_y) ?? 0)), style: ctrlInput, step: 10 })
            ] }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "rotate", (adj.rotate + 1) % 4), style: ctrlBtn, children: "↻ 旋转" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "mirrorX", !adj.mirrorX), style: { ...ctrlBtn, background: adj.mirrorX ? "#4CAF50" : "#555" }, children: "⇄ 左右" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "mirrorY", !adj.mirrorY), style: { ...ctrlBtn, background: adj.mirrorY ? "#4CAF50" : "#555" }, children: "⇅ 上下" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdjOffsets((prev) => {
                const n = { ...prev };
                delete n[mapName];
                return n;
              }), style: ctrlBtn, children: "↺ 重置" })
            ] })
          ] })
        ] }, mapName);
      })
    ] })) }),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
      marginTop: 10,
      padding: 10,
      background: "#3a3a3a",
      borderRadius: 5,
      fontSize: 15,
      textAlign: "center",
      color: "#aaa"
    }, children: [
      /* @__PURE__ */ jsxRuntime.jsx("strong", { children: "颜色说明：" }),
      /* @__PURE__ */ jsxRuntime.jsx("span", { style: { display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#00ffff", marginRight: 3 } }),
      " Z > 299 (高于地面)",
      /* @__PURE__ */ jsxRuntime.jsx("span", { style: { display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#ffff00", margin: "0 3px 0 12px" } }),
      " -299 ≤ Z ≤ 299 (正常高度)",
      /* @__PURE__ */ jsxRuntime.jsx("span", { style: { display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#ff4444", margin: "0 3px 0 12px" } }),
      " Z < -299 (低于地面)",
      /* @__PURE__ */ jsxRuntime.jsx("br", {}),
      /* @__PURE__ */ jsxRuntime.jsxs("strong", { children: [
        "位置统计：共 ",
        coords.length,
        " 个位置点"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("br", {}),
      /* @__PURE__ */ jsxRuntime.jsx("strong", { children: "包含地图：" }),
      " ",
      [...grouped.keys()].map((k) => {
        var _a;
        return ((_a = modules.get(k)) == null ? void 0 : _a.translation) || k;
      }).join(", ")
    ] }),
    debug && (() => {
      const rows = coords.map((c, i) => {
        const mod = modules.get(c.map);
        const g = (mod == null ? void 0 : mod.group) || "";
        const rowKey = `${c.file}-${i}`;
        return {
          key: rowKey,
          group: GROUP_LABELS$1[g] || g,
          groupKey: g,
          file: c.file,
          mapName: c.map,
          mapLabel: (mod == null ? void 0 : mod.translation) || c.map,
          label: c.label || "",
          x: c.x,
          y: c.y,
          z: c.z,
          hidden: hiddenRows.has(rowKey)
        };
      });
      function batchToggle(pred) {
        const matched = rows.filter(pred);
        if (matched.length === 0) return;
        const allHidden = matched.every((r) => r.hidden);
        for (const r of matched) {
          if (allHidden && r.hidden) toggleRow(r.key);
          else if (!allHidden && !r.hidden) toggleRow(r.key);
        }
      }
      return /* @__PURE__ */ jsxRuntime.jsx(
        DebugCoordTable,
        {
          rows,
          onToggleRow: toggleRow,
          onToggleGroup: (gk) => batchToggle((r) => r.groupKey === gk),
          onToggleFile: (f) => batchToggle((r) => r.file === f),
          onToggleMap: (mn) => batchToggle((r) => r.mapName === mn),
          onToggleLabel: (l) => batchToggle((r) => r.label === l)
        }
      );
    })()
  ] });
}
const GROUP_LABELS = {
  Crypt: "废墟2层地牢",
  FireDeep: "哥布林洞穴2层",
  GoblinCave: "哥布林洞穴1层",
  IceAbyss: "冰图2层",
  IceCavern: "冰图1层",
  Inferno: "废墟3层炼狱",
  Ruins: "废墟1层",
  ShipGraveyard: "水图"
};
function zColor(z) {
  if (z > 299) return "#00ffff";
  if (z >= -299) return "#ffff00";
  return "#ff3333";
}
const GLOW = "0 0 4px #fff, 0 0 2px #000";
function LootdropDetailPage() {
  var _a;
  const { name } = reactRouterDom.useParams();
  const dataKey = `lootdrops/${name ? decodeURIComponent(name) : ""}`;
  const ssrData = useSSRData(dataKey);
  const [data, setData] = react.useState((ssrData == null ? void 0 : ssrData.item) || null);
  const [modules, setModules] = react.useState(
    ssrData ? new Map(ssrData.modules.map((m) => [m.name, m])) : /* @__PURE__ */ new Map()
  );
  const [loading, setLoading] = react.useState(!ssrData);
  const [hidden, setHidden] = react.useState(/* @__PURE__ */ new Set());
  const [hiddenRows, setHiddenRows] = react.useState(/* @__PURE__ */ new Set());
  const { debug, toggle: toggleDebug, adjOffsets, setAdjOffsets } = useDebug();
  react.useEffect(() => {
    if (!name) return;
    if (ssrData) return;
    Promise.all([
      fetch(`./data/json/lootdrops/${decodeURIComponent(name)}.json`).then((r) => r.json()),
      fetch(`./data/json/dungeon_modules.json`).then((r) => r.json())
    ]).then(([item, mods]) => {
      setData(item);
      const mm = /* @__PURE__ */ new Map();
      mods.forEach((m) => {
        mm.set(m.name, m);
        mm.set(m.sl_base_name, m);
      });
      setModules(mm);
    }).catch(console.error).finally(() => setLoading(false));
  }, [name]);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  if (!data) return /* @__PURE__ */ jsxRuntime.jsx("div", { style: { textAlign: "center", color: "#ff6b6b", marginTop: 100 }, children: "未找到" });
  function myGetAdj(mapName, mod) {
    return getAdj(mapName, mod == null ? void 0 : mod.rotate, adjOffsets);
  }
  function setAdj(mapName, field, value) {
    setAdjOffsets((prev) => {
      const cur = prev[mapName] || { x: 0, y: 0, range: 0, rotate: 0, mirrorX: false, mirrorY: false };
      return { ...prev, [mapName]: { ...cur, [field]: value } };
    });
  }
  const toggle = (monsterName) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(monsterName)) next.delete(monsterName);
      else next.add(monsterName);
      return next;
    });
  };
  const toggleRow = (key) => {
    setHiddenRows((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };
  const mapGroups = /* @__PURE__ */ new Map();
  for (const m of data.monsters) {
    if (hidden.has(m.name)) continue;
    for (const c of m.coords) {
      if (!mapGroups.has(c.map)) mapGroups.set(c.map, { mod: modules.get(c.map), dots: [] });
      mapGroups.get(c.map).dots.push({ monster: m, x: c.x, y: c.y, z: c.z, file: c.file });
    }
  }
  const groupedByType = /* @__PURE__ */ new Map();
  const items = [...mapGroups.entries()].map(([mapName, { mod, dots }]) => ({ mapName, mod, dots }));
  items.sort((a, b) => {
    var _a2, _b, _c, _d;
    const sy_a = ((_a2 = a.mod) == null ? void 0 : _a2.size_y) ?? 1;
    const sy_b = ((_b = b.mod) == null ? void 0 : _b.size_y) ?? 1;
    const sx_a = ((_c = a.mod) == null ? void 0 : _c.size_x) ?? 1;
    const sx_b = ((_d = b.mod) == null ? void 0 : _d.size_x) ?? 1;
    return sy_a - sy_b || sx_a - sx_b;
  });
  for (const item of items) {
    const g = ((_a = item.mod) == null ? void 0 : _a.group) || "";
    if (!groupedByType.has(g)) groupedByType.set(g, []);
    groupedByType.get(g).push(item);
  }
  const groupOrder = Object.keys(GROUP_LABELS);
  const sortedGroups = [...groupedByType.entries()].sort(([a], [b]) => groupOrder.indexOf(a) - groupOrder.indexOf(b));
  const totalCoords = data.monsters.reduce((s, m) => s + (hidden.has(m.name) ? 0 : m.coords.length), 0);
  const visibleCount = data.monsters.filter((m) => !hidden.has(m.name)).length;
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: toggleDebug, style: {
      position: "fixed",
      top: 20,
      right: 20,
      padding: "4px 16px",
      background: debug ? "#4CAF50" : "#FFC107",
      color: debug ? "#fff" : "#000",
      border: debug ? "2px solid #388E3C" : "2px solid #FF9800",
      borderRadius: 6,
      cursor: "pointer",
      fontSize: 13,
      fontWeight: "bold",
      zIndex: 9999,
      boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
    }, children: debug ? "退出调试" : "显示调试信息" }),
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsxs("title", { children: [
        data.translation || data.name,
        " 掉落来源 | DarkFindV5游戏导航"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "{data.translation || data.name} 由 {visibleCount} 个怪物掉落，共 {totalCoords} 个位置点。" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:title", content: "{data.translation || data.name} 掉落来源 | DarkFindV5" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { property: "og:description", content: "{data.translation || data.name} 由 {visibleCount} 个怪物掉落" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsxs("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 28, margin: "0 0 8px" }, children: [
      data.translation,
      " >> ",
      data.monsters.filter((m) => !hidden.has(m.name)).map((m) => m.translation).join("、"),
      data.monsters.length - visibleCount > 0 && /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#888", fontSize: 16 }, children: [
        " (+",
        data.monsters.length - visibleCount,
        ")"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#aaa", fontSize: 14, marginLeft: 12 }, children: [
        data.monsters.length,
        "种坐标汇总"
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx(Disclaimer, {}),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", margin: "15px 0", padding: 10, background: "#3a3a3a", borderRadius: 5 }, children: [
      /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => {
        const allHidden = data.monsters.every((m) => hidden.has(m.name));
        if (allHidden || hidden.size === data.monsters.length) {
          setHidden(/* @__PURE__ */ new Set());
        } else {
          setHidden(new Set(data.monsters.map((m) => m.name)));
        }
      }, style: {
        padding: "8px 15px",
        border: "2px solid #888",
        borderRadius: 5,
        cursor: "pointer",
        fontSize: 14,
        fontWeight: "bold",
        color: "#ccc",
        background: "transparent",
        transition: "all 0.2s"
      }, children: hidden.size === 0 ? "隐藏全部" : "全部显示" }),
      data.monsters.map((m) => /* @__PURE__ */ jsxRuntime.jsxs("button", { onClick: () => toggle(m.name), style: {
        padding: "8px 15px",
        border: `2px solid ${m.color}`,
        borderRadius: 5,
        cursor: "pointer",
        fontSize: 14,
        fontWeight: "bold",
        color: "#fff",
        background: hidden.has(m.name) ? "transparent" : m.color,
        opacity: hidden.has(m.name) ? 0.3 : 1,
        transition: "all 0.2s"
      }, children: [
        m.translation,
        " (",
        m.coords.length,
        ")"
      ] }, m.name))
    ] }),
    debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center", margin: "10px 0", padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 14, color: "#aaa" }, children: [
      /* @__PURE__ */ jsxRuntime.jsx("strong", { style: { color: "#ccc" }, children: "怪物图例：" }),
      data.monsters.map((m) => /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { display: "flex", alignItems: "center", gap: 5, cursor: "pointer", opacity: hidden.has(m.name) ? 0.3 : 1 }, onClick: () => toggle(m.name), children: [
        /* @__PURE__ */ jsxRuntime.jsx("span", { style: { width: 12, height: 12, borderRadius: "50%", background: m.color } }),
        m.translation,
        " ",
        /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#888" }, children: [
          "(",
          m.coords.length,
          ")"
        ] })
      ] }, m.name))
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx("div", { style: { display: "grid", gap: 6, gridTemplateColumns: "repeat(4, 1fr)" }, children: sortedGroups.map(([groupName, groupItems]) => /* @__PURE__ */ jsxRuntime.jsxs(jsxRuntime.Fragment, { children: [
      groupName && /* @__PURE__ */ jsxRuntime.jsx("div", { style: { gridColumn: "1 / -1", fontSize: 22, fontWeight: "bold", color: "#FFC107", padding: "5px 0", marginTop: 10, borderBottom: "2px solid #FFC107" }, children: GROUP_LABELS[groupName] || groupName }, `h-${groupName}`),
      groupItems.map(({ mapName, mod, dots }) => {
        var _a2;
        const sx = (mod == null ? void 0 : mod.size_x) ?? 1;
        const sy = (mod == null ? void 0 : mod.size_y) ?? 1;
        const baseRange = (mod == null ? void 0 : mod.range) || Math.max(sx, sy) * 1600 || 1600;
        const adj = myGetAdj(mapName, mod);
        const range = baseRange + adj.range || 1600;
        const offX = ((mod == null ? void 0 : mod.offset_x) ?? 0) + adj.x;
        const offY = ((mod == null ? void 0 : mod.offset_y) ?? 0) + adj.y;
        return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { minWidth: 0, gridColumn: sx >= 2 ? `span ${sx}` : void 0, gridRow: sy >= 2 ? `span ${sy}` : void 0, background: "#3a3a3a", border: "1px solid #555", borderRadius: 5, padding: 8 }, children: [
          /* @__PURE__ */ jsxRuntime.jsxs("h3", { style: { margin: "0 0 6px 0", fontSize: 22, color: "#00bcd4", textAlign: "center", width: "100%", lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, children: [
            (mod == null ? void 0 : mod.translation) || mapName,
            debug && /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#888", fontSize: 11 }, children: [
              " (",
              mapName,
              ")"
            ] })
          ] }),
          debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4 }, children: [
            (mod == null ? void 0 : mod.img_name) || (mod == null ? void 0 : mod.sl_base_name) || mapName,
            ".webp | 找到 ",
            dots.length,
            " 个位置 | 范围: ±",
            range
          ] }),
          debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { fontSize: 10, color: "#888", textAlign: "center", marginBottom: 4, lineHeight: 1.4 }, children: [
            ((_a2 = dots[0]) == null ? void 0 : _a2.file) || "",
            /* @__PURE__ */ jsxRuntime.jsx("br", {}),
            "旋转:",
            (mod == null ? void 0 : mod.rotate) ?? 0,
            " 偏移:(",
            (mod == null ? void 0 : mod.offset_x) ?? 0,
            ",",
            (mod == null ? void 0 : mod.offset_y) ?? 0,
            ") 大小:",
            sx,
            "x",
            sy
          ] }),
          debug && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { fontSize: 11, color: "#aaa", marginBottom: 4, display: "flex", flexDirection: "column", gap: 3 }, children: [
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888" }, children: "范围:" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "range", Math.round(range / 2) - baseRange), style: ctrlBtn, children: "÷2" }),
              /* @__PURE__ */ jsxRuntime.jsx("input", { type: "number", value: range, onChange: (e) => setAdj(mapName, "range", Number(e.target.value) - baseRange), style: ctrlInput, step: 100 }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "range", range * 2 - baseRange), style: ctrlBtn, children: "x2" }),
              /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#aaa", fontSize: 12, marginLeft: 4 }, children: [
                "↻",
                adj.rotate
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888" }, children: "偏移:" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "y", adj.y - 50), style: ctrlBtn, children: "↑" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "y", adj.y + 50), style: ctrlBtn, children: "↓" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "x", adj.x - 50), style: ctrlBtn, children: "←" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "x", adj.x + 50), style: ctrlBtn, children: "→" }),
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888", marginLeft: 8 }, children: "X:" }),
              /* @__PURE__ */ jsxRuntime.jsx("input", { type: "number", value: offX, onChange: (e) => setAdj(mapName, "x", Number(e.target.value) - ((mod == null ? void 0 : mod.offset_x) ?? 0)), style: ctrlInput, step: 10 }),
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { color: "#888" }, children: "Y:" }),
              /* @__PURE__ */ jsxRuntime.jsx("input", { type: "number", value: offY, onChange: (e) => setAdj(mapName, "y", Number(e.target.value) - ((mod == null ? void 0 : mod.offset_y) ?? 0)), style: ctrlInput, step: 10 })
            ] }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "rotate", (adj.rotate + 1) % 4), style: ctrlBtn, children: "↻ 旋转" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "mirrorX", !adj.mirrorX), style: { ...ctrlBtn, background: adj.mirrorX ? "#4CAF50" : "#555" }, children: "⇄ 左右" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdj(mapName, "mirrorY", !adj.mirrorY), style: { ...ctrlBtn, background: adj.mirrorY ? "#4CAF50" : "#555" }, children: "⇅ 上下" }),
              /* @__PURE__ */ jsxRuntime.jsx("button", { onClick: () => setAdjOffsets((prev) => {
                const n = { ...prev };
                delete n[mapName];
                return n;
              }), style: ctrlBtn, children: "↺ 重置" })
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntime.jsx("div", { style: { aspectRatio: `${sx} / ${sy}`, background: "#2c2c2c", border: "1px solid #666", borderRadius: 4, position: "relative", overflow: "hidden", backgroundImage: `url(./data/img/${(mod == null ? void 0 : mod.img_name) || (mod == null ? void 0 : mod.sl_base_name) || "RareModule_1x1"}.webp)`, backgroundSize: "cover", backgroundPosition: "center" }, children: dots.map((d, i) => {
            const [x, y] = applyTransform(d.x, d.y, offX, offY, adj);
            const [px, py] = computePixel(x, y, range, sx, sy);
            const col = d.monster.color;
            const zcol = zColor(d.z);
            const textCol = zcol === "#ff3333" ? "#ffffff" : zcol;
            const textShadow = zcol === "#ff3333" ? "0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000" : GLOW;
            return /* @__PURE__ */ jsxRuntime.jsx("div", { title: d.monster.translation, style: { position: "absolute", left: `${px}%`, top: `${py}%`, width: 9, height: 9, borderRadius: "50%", background: col, boxShadow: `0 0 6px ${col}`, border: "1px solid #fff", transform: "translate(-50%, -50%)", zIndex: 10 }, children: /* @__PURE__ */ jsxRuntime.jsx("span", { style: { position: "absolute", left: "50%", top: "100%", transform: "translateX(-50%)", fontSize: 11, fontFamily: "Arial, sans-serif", color: textCol, whiteSpace: "nowrap", textShadow, lineHeight: 1, marginTop: 1 }, children: Math.round(d.z) }) }, i);
          }) }),
          /* @__PURE__ */ jsxRuntime.jsx("div", { style: { display: "flex", flexWrap: "wrap", gap: "4px 10px", justifyContent: "center", marginTop: 5, fontSize: 13, color: "#ccc", alignItems: "center" }, children: [...new Set(dots.map((d) => d.monster.name))].map((mn) => {
            const m = data.monsters.find((x) => x.name === mn);
            return /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { display: "flex", alignItems: "center", gap: 3 }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { width: 10, height: 10, borderRadius: "50%", background: m.color, flexShrink: 0 } }),
              /* @__PURE__ */ jsxRuntime.jsx("span", { style: { cursor: "pointer" }, onClick: () => toggle(mn), children: m.translation }),
              /* @__PURE__ */ jsxRuntime.jsxs("span", { style: { color: "#888" }, children: [
                "(",
                dots.filter((d) => d.monster.name === mn).length,
                "点)"
              ] })
            ] }, mn);
          }) })
        ] }, mapName);
      })
    ] })) }),
    debug && (() => {
      const rows = data.monsters.filter((m) => !hidden.has(m.name)).flatMap(
        (m) => m.coords.map((c, j) => {
          const mod = modules.get(c.map);
          const g = (mod == null ? void 0 : mod.group) || "";
          const rowKey = `${m.name}-${j}`;
          return {
            key: rowKey,
            group: GROUP_LABELS[g] || g,
            monster: { name: m.name, translation: m.translation, color: m.color, onToggle: () => toggle(m.name) },
            file: c.file,
            mapName: c.map,
            mapLabel: (mod == null ? void 0 : mod.translation) || c.map,
            label: c.label || "",
            x: c.x,
            y: c.y,
            z: c.z,
            hidden: hiddenRows.has(rowKey)
          };
        })
      );
      return /* @__PURE__ */ jsxRuntime.jsx(
        DebugCoordTable,
        {
          rows,
          onToggleRow: toggleRow,
          onToggleMap: (mapName) => {
            const mapRows = rows.filter((r) => r.mapName === mapName);
            const allHidden = mapRows.every((r) => r.hidden);
            for (const r of mapRows) {
              if (allHidden) toggleRow(r.key);
              else if (hiddenRows.has(r.key)) ;
              else toggleRow(r.key);
            }
          },
          showMonster: true
        }
      );
    })(),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { marginTop: 10, padding: 10, background: "#3a3a3a", borderRadius: 5, fontSize: 15, textAlign: "center", color: "#aaa" }, children: [
      /* @__PURE__ */ jsxRuntime.jsxs("strong", { children: [
        "位置统计：共 ",
        totalCoords,
        " 个位置点"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("br", {}),
      /* @__PURE__ */ jsxRuntime.jsx("strong", { children: "包含地图：" }),
      " ",
      [.../* @__PURE__ */ new Set([...mapGroups.keys()])].map((k) => {
        var _a2;
        return ((_a2 = modules.get(k)) == null ? void 0 : _a2.translation) || k;
      }).join("、")
    ] })
  ] });
}
function ExplorePage() {
  const ssrData = useSSRData("explore");
  const [data, setData] = react.useState(ssrData || []);
  const [loading, setLoading] = react.useState(!ssrData);
  react.useEffect(() => {
    if (ssrData) return;
    fetch("./data/json/explore.json").then((r) => r.json()).then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  const grouped = /* @__PURE__ */ new Map();
  for (const t of data) {
    const key = t.npc_name_display || t.npc_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(t);
  }
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsx("title", { children: "探索地点表 | DarkFindV5游戏导航" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "探索目标汇总——{data.length} 个探索目标，分布在 {grouped.size} 个NPC。" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }, children: "【探索地点表】探索目标汇总" }),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }, children: [
      "共 ",
      data.length,
      " 个探索目标，分布在 ",
      grouped.size,
      " 个NPC"
    ] }),
    [...grouped.entries()].map(([npcName, targets]) => /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { marginBottom: 24 }, children: [
      /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
        fontSize: 22,
        fontWeight: "bold",
        color: "#FFC107",
        padding: "5px 0",
        borderBottom: "2px solid #FFC107",
        marginBottom: 12
      }, children: [
        npcName,
        " (",
        targets.length,
        ")"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("div", { style: {
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 16
      }, children: targets.map((t, i) => /* @__PURE__ */ jsxRuntime.jsxs(
        "div",
        {
          style: {
            background: "#3a3a3a",
            border: "1px solid #555",
            borderRadius: 8,
            padding: 16,
            cursor: "pointer",
            transition: "transform 0.2s"
          },
          onMouseEnter: (e) => e.currentTarget.style.transform = "translateY(-3px)",
          onMouseLeave: (e) => e.currentTarget.style.transform = "none",
          children: [
            /* @__PURE__ */ jsxRuntime.jsx("div", { style: { color: "#00bcd4", fontSize: 16, fontWeight: "bold", marginBottom: 6 }, children: t.name || t.module_name }),
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#aaa", fontSize: 12 }, children: [
              "任务: ",
              t.quest_title || `#${t.quest_number}`
            ] }),
            /* @__PURE__ */ jsxRuntime.jsx("div", { style: { color: "#888", fontSize: 11, marginTop: 4 }, children: t.module_name })
          ]
        },
        i
      )) })
    ] }, npcName))
  ] });
}
function QuestItemsPage() {
  const ssrData = useSSRData("quest_items");
  const [data, setData] = react.useState(ssrData || []);
  const [loading, setLoading] = react.useState(!ssrData);
  react.useEffect(() => {
    if (ssrData) return;
    fetch("./data/json/quest_items.json").then((r) => r.json()).then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  const grouped = /* @__PURE__ */ new Map();
  for (const t of data) {
    const key = t.npc_name_cn || t.npc_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(t);
  }
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsx("title", { children: "任务物品表 | DarkFindV5游戏导航" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "任务物品查询——按地图分组查看任务物品分布。" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }, children: "【任务物品表】任务物品汇总" }),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }, children: [
      "共 ",
      data.length,
      " 个任务物品，分布在 ",
      grouped.size,
      " 个NPC"
    ] }),
    [...grouped.entries()].map(([npcName, items]) => /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { marginBottom: 24 }, children: [
      /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
        fontSize: 22,
        fontWeight: "bold",
        color: "#FFC107",
        padding: "5px 0",
        borderBottom: "2px solid #FFC107",
        marginBottom: 12
      }, children: [
        npcName,
        " (",
        items.length,
        ")"
      ] }),
      /* @__PURE__ */ jsxRuntime.jsx("div", { style: {
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 12
      }, children: items.map((qi, i) => /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
        background: "#3a3a3a",
        border: "1px solid #555",
        borderRadius: 6,
        padding: 12,
        fontSize: 13
      }, children: [
        /* @__PURE__ */ jsxRuntime.jsx("div", { style: { color: "#E91E63", fontWeight: "bold", marginBottom: 4 }, children: qi.item_translation || qi.item_name }),
        /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#aaa" }, children: [
          "任务 #",
          qi.quest_number,
          " ×",
          qi.count,
          qi.rarity && /* @__PURE__ */ jsxRuntime.jsx("span", { style: { marginLeft: 8, color: "#FFC107" }, children: qi.rarity }),
          qi.is_loot && /* @__PURE__ */ jsxRuntime.jsx("span", { style: { marginLeft: 8, color: "#4CAF50" }, children: "已拾取" })
        ] }),
        /* @__PURE__ */ jsxRuntime.jsx("div", { style: { color: "#888", fontSize: 11, marginTop: 2 }, children: qi.item_name })
      ] }, i)) })
    ] }, npcName))
  ] });
}
function QuestNPCPage() {
  const ssrData = useSSRData("quest_npc");
  const [data, setData] = react.useState(ssrData || []);
  const [loading, setLoading] = react.useState(!ssrData);
  const [expanded, setExpanded] = react.useState(null);
  react.useEffect(() => {
    if (ssrData) return;
    fetch("./data/json/quest_npc.json").then((r) => r.json()).then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);
  if (loading) return /* @__PURE__ */ jsxRuntime.jsx(antd.Spin, { size: "large", style: { display: "block", margin: "100px auto" } });
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { maxWidth: 1200, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs(reactHelmetAsync.Helmet, { children: [
      /* @__PURE__ */ jsxRuntime.jsx("title", { children: "任务NPC表 | DarkFindV5游戏导航" }),
      /* @__PURE__ */ jsxRuntime.jsx("meta", { name: "description", content: "NPC任务详情查询——查看各NPC的任务、奖励、需求。" })
    ] }),
    /* @__PURE__ */ jsxRuntime.jsx("h1", { style: { textAlign: "center", color: "#00bcd4", fontSize: 36, marginBottom: 20 }, children: "【任务NPC表】NPC任务详情" }),
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { textAlign: "center", color: "#aaa", fontSize: 14, marginBottom: 20 }, children: [
      "共 ",
      data.length,
      " 个活跃NPC"
    ] }),
    (() => {
      const grouped = /* @__PURE__ */ new Map();
      for (const npc of data) {
        const cat = npc.category || "其他";
        if (!grouped.has(cat)) grouped.set(cat, []);
        grouped.get(cat).push(npc);
      }
      const order = ["装备NPC", "优选NPC", "可用NPC", ""];
      return [...grouped.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
    })().map(([category, npcs]) => /* @__PURE__ */ jsxRuntime.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
        fontSize: 22,
        fontWeight: "bold",
        color: "#FFC107",
        padding: "5px 0",
        borderBottom: "2px solid #FFC107",
        marginBottom: 12,
        marginTop: 24
      }, children: [
        category || "其他",
        " (",
        npcs.length,
        ")"
      ] }),
      npcs.map((npc) => /* @__PURE__ */ jsxRuntime.jsxs(
        "div",
        {
          style: {
            background: "#3a3a3a",
            border: "1px solid #555",
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
            cursor: "pointer"
          },
          onClick: () => setExpanded(expanded === npc.npc_name ? null : npc.npc_name),
          children: [
            /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [
              /* @__PURE__ */ jsxRuntime.jsx("div", { style: { color: "#00bcd4", fontSize: 20, fontWeight: "bold" }, children: npc.npc_name_display }),
              /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#aaa", fontSize: 13 }, children: [
                npc.quest_count,
                " 个任务"
              ] })
            ] }),
            expanded === npc.npc_name && /* @__PURE__ */ jsxRuntime.jsx("div", { style: { marginTop: 12 }, children: npc.quests.map((q) => /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
              background: "#2c2c2c",
              border: "1px solid #444",
              borderRadius: 6,
              padding: 12,
              marginBottom: 8
            }, children: [
              /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#FFC107", fontWeight: "bold", marginBottom: 4 }, children: [
                "#",
                q.quest_number,
                " ",
                q.title
              ] }),
              q.greeting && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#aaa", fontSize: 12, marginBottom: 4 }, children: [
                "接取: ",
                q.greeting
              ] }),
              q.complete && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#aaa", fontSize: 12, marginBottom: 4 }, children: [
                "完成: ",
                q.complete
              ] }),
              q.rewards.length > 0 && /* @__PURE__ */ jsxRuntime.jsx("div", { style: { marginTop: 4 }, children: q.rewards.map((r, ri) => /* @__PURE__ */ jsxRuntime.jsxs(antd.Tag, { color: "green", style: { fontSize: 11 }, children: [
                r.id,
                " ×",
                r.count
              ] }, ri)) }),
              q.required && /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { color: "#888", fontSize: 11, marginTop: 4 }, children: [
                "前置: ",
                q.required
              ] })
            ] }, q.id)) })
          ]
        },
        npc.npc_name
      ))
    ] }, category))
  ] });
}
const LABEL_MAP = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
  lootdrops: "掉落表",
  explore: "探索地点表",
  quest_items: "任务物品表",
  quest_npc: "任务NPC表"
};
function NavBar() {
  const location = reactRouterDom.useLocation();
  const navigate = reactRouterDom.useNavigate();
  const { dark, tokens, toggle } = useTheme();
  const parts = location.pathname.split("/").filter(Boolean);
  const linkStyle = {
    color: tokens.accent,
    textDecoration: "none",
    fontSize: 15,
    fontWeight: "bold",
    padding: "6px 16px",
    border: `1px solid ${tokens.accent}`,
    borderRadius: 5,
    cursor: "pointer",
    transition: "all 0.2s"
  };
  const listPart = parts[0] ? { label: LABEL_MAP[parts[0]] || parts[0], path: "/" + parts[0] } : null;
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: {
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 8,
    maxWidth: 1200,
    margin: "0 auto 15px",
    padding: "8px 20px",
    background: tokens.surface,
    borderRadius: 5
  }, children: [
    /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { display: "flex", alignItems: "center", gap: 6 }, children: [
      /* @__PURE__ */ jsxRuntime.jsx(icons.BulbOutlined, { style: { color: dark ? "#ffd700" : "#333", fontSize: 16 } }),
      /* @__PURE__ */ jsxRuntime.jsx(antd.Switch, { checked: !dark, onChange: toggle, size: "small" })
    ] }),
    listPart && parts.length >= 2 && /* @__PURE__ */ jsxRuntime.jsx(
      "a",
      {
        onClick: () => navigate(listPart.path),
        style: linkStyle,
        onMouseEnter: (e) => {
          e.currentTarget.style.background = tokens.accent;
          e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff";
        },
        onMouseLeave: (e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = tokens.accent;
        },
        children: listPart.label
      }
    ),
    /* @__PURE__ */ jsxRuntime.jsx(
      "a",
      {
        onClick: () => navigate("/"),
        style: linkStyle,
        onMouseEnter: (e) => {
          e.currentTarget.style.background = tokens.accent;
          e.currentTarget.style.color = dark ? "#2c2c2c" : "#fff";
        },
        onMouseLeave: (e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = tokens.accent;
        },
        children: "返回首页"
      }
    )
  ] });
}
function AppInner() {
  const { tokens } = useTheme();
  return /* @__PURE__ */ jsxRuntime.jsxs("div", { style: { minHeight: "100vh", padding: "24px", background: tokens.bg }, children: [
    /* @__PURE__ */ jsxRuntime.jsx(NavBar, {}),
    /* @__PURE__ */ jsxRuntime.jsxs(reactRouterDom.Routes, { children: [
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/", element: /* @__PURE__ */ jsxRuntime.jsx(HomePage, {}) }),
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/explore", element: /* @__PURE__ */ jsxRuntime.jsx(ExplorePage, {}) }),
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/quest_items", element: /* @__PURE__ */ jsxRuntime.jsx(QuestItemsPage, {}) }),
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/quest_npc", element: /* @__PURE__ */ jsxRuntime.jsx(QuestNPCPage, {}) }),
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/:page", element: /* @__PURE__ */ jsxRuntime.jsx(ListPage, {}) }),
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/lootdrops/:name", element: /* @__PURE__ */ jsxRuntime.jsx(LootdropDetailPage, {}) }),
      /* @__PURE__ */ jsxRuntime.jsx(reactRouterDom.Route, { path: "/:page/:name", element: /* @__PURE__ */ jsxRuntime.jsx(DetailPage, {}) })
    ] })
  ] });
}
globalThis.window = globalThis;
const styleEl = {
  className: "",
  setAttribute: () => {
  },
  removeAttribute: () => {
  },
  insertAdjacentElement: () => null,
  textContent: "",
  sheet: { cssRules: [], insertRule: () => {
  }, removeRule: () => {
  } },
  parentNode: { removeChild: () => {
  } },
  appendChild: () => {
  },
  insertBefore: () => {
  }
};
globalThis.document = {
  createElement: (tag) => {
    if (tag === "style") return { ...styleEl, tagName: "STYLE" };
    if (tag === "meta") return { ...styleEl, tagName: "META" };
    if (tag === "link") return { ...styleEl, tagName: "LINK" };
    return { className: "", style: {}, setAttribute: () => {
    }, removeAttribute: () => {
    }, appendChild: () => {
    }, insertAdjacentElement: () => null, textContent: "", parentNode: { removeChild: () => {
    } } };
  },
  createTextNode: () => ({}),
  getElementsByTagName: () => [],
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: { style: {} },
  head: { appendChild: () => {
  }, querySelectorAll: () => [], insertBefore: () => {
  } },
  body: { appendChild: () => {
  }, removeChild: () => {
  } }
};
globalThis.navigator = { userAgent: "node" };
globalThis.location = { href: "", pathname: "", search: "", hash: "" };
globalThis.getComputedStyle = () => ({});
function render(url, ssrDataMap) {
  var _a, _b;
  const helmetContext = { helmet: {} };
  const html = server.renderToString(
    /* @__PURE__ */ jsxRuntime.jsx(reactHelmetAsync.HelmetProvider, { context: helmetContext, children: /* @__PURE__ */ jsxRuntime.jsx(
      antd.ConfigProvider,
      {
        locale: zhCN,
        theme: { algorithm: antd.theme.darkAlgorithm, token: { colorPrimary: "#1677ff" } },
        children: /* @__PURE__ */ jsxRuntime.jsx(ThemeProvider, { children: /* @__PURE__ */ jsxRuntime.jsx(DebugProvider, { children: /* @__PURE__ */ jsxRuntime.jsx(SSRDataContext.Provider, { value: ssrDataMap, children: /* @__PURE__ */ jsxRuntime.jsx(server_mjs.StaticRouter, { location: url, children: /* @__PURE__ */ jsxRuntime.jsx(AppInner, {}) }) }) }) })
      }
    ) })
  );
  console.log("[ssr] url:", url);
  console.log("[ssr] helmetContext:", JSON.stringify(helmetContext, null, 2));
  const { helmet } = helmetContext;
  return {
    html,
    head: [
      ((_a = helmet == null ? void 0 : helmet.title) == null ? void 0 : _a.toString()) ?? "",
      ((_b = helmet == null ? void 0 : helmet.meta) == null ? void 0 : _b.toString()) ?? ""
    ].join("").trim()
  };
}
exports.render = render;
