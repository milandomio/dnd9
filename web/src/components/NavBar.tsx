import { useState, useEffect, useRef, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Input, Switch } from "antd";
import { BulbOutlined, SearchOutlined } from "@ant-design/icons";
import { useTheme } from "../hooks/useTheme";

const LABEL_MAP: Record<string, string> = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
  lootdrops: "掉落表",
  explore: "探索地点表",
  quest_items: "任务物品表",
  quest_npc: "任务NPC表",
  dungeon_modules: "地图模块表",
};

const PAGE_TAG: Record<string, string> = {
  items: "物品",
  monsters: "怪物",
  props: "实体",
  lootdrops: "掉落",
  explore: "探索",
  quest_npc: "NPC",
  quest_items: "任务",
  dungeon_modules: "模块",
};

interface SearchHit {
  name: string;
  translation: string;
  page: string;
  url: string;
  tag?: string;
}

async function buildSearchIndex(): Promise<SearchHit[]> {
  try {
    const resp = await fetch("./data/json/search_index.json");
    if (!resp.ok) return [];
    return await resp.json();
  } catch {
    return [];
  }
}

export default function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { dark, tokens, toggle } = useTheme();
  const parts = location.pathname.split("/").filter(Boolean);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchIndex, setSearchIndex] = useState<SearchHit[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  const ensureIndex = useCallback(async () => {
    if (searchIndex !== null || loading) return;
    setLoading(true);
    try {
      const index = await buildSearchIndex();
      setSearchIndex(index);
    } finally {
      setLoading(false);
    }
  }, [searchIndex, loading]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setShowDropdown(false);
      return;
    }
    if (!searchIndex) return;
    const q = query.toLowerCase();
    const filtered = searchIndex.filter(
      (e) => e.name.toLowerCase().includes(q) || e.translation.toLowerCase().includes(q)
    ).slice(0, 50);
    setResults(filtered);
    setShowDropdown(filtered.length > 0);
    setSelectedIdx(-1);
  }, [query, searchIndex]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (hit: SearchHit) => {
    setQuery("");
    setShowDropdown(false);
    navigate(hit.url);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      if (selectedIdx >= 0 && results[selectedIdx]) {
        handleSelect(results[selectedIdx]);
      }
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  };

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
      justifyContent: "space-between",
      gap: 8,
      maxWidth: 1200,
      margin: "0 auto 15px",
      padding: "8px 20px",
      background: tokens.surface,
      borderRadius: 5,
    }}>
      <div ref={searchRef} style={{ position: "relative", flex: "0 1 320px" }}>
        <Input
          ref={inputRef}
          prefix={<SearchOutlined style={{ color: tokens.muted }} />}
          placeholder="搜索物品/怪物/实体..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { ensureIndex(); if (results.length > 0) setShowDropdown(true); }}
          onKeyDown={handleKeyDown}
          allowClear
          style={{
            background: dark ? "#333" : "#fff",
            borderColor: tokens.border,
            color: tokens.text,
            borderRadius: 6,
          }}
        />
        {showDropdown && (
          <div style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            marginTop: 4,
            background: dark ? "#2c2c2c" : "#fff",
            border: `1px solid ${tokens.border}`,
            borderRadius: 6,
            maxHeight: 400,
            overflowY: "auto",
            zIndex: 1000,
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}>
            {results.map((hit, i) => (
              <div
                key={`${hit.page}::${hit.name}`}
                onClick={() => handleSelect(hit)}
                onMouseEnter={() => setSelectedIdx(i)}
                style={{
                  padding: "8px 12px",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: i === selectedIdx ? (dark ? "#444" : "#e6f4ff") : "transparent",
                  transition: "background 0.1s",
                }}
              >
                <span style={{ color: tokens.text, fontSize: 14 }}>
                  {hit.translation || hit.name}
                  {hit.translation && hit.translation !== hit.name && (
                    <span style={{ color: tokens.muted, marginLeft: 6, fontSize: 12 }}>
                      ({hit.name})
                    </span>
                  )}
                </span>
                <span style={{
                  fontSize: 11,
                  padding: "1px 6px",
                  borderRadius: 3,
                  background: dark ? "#555" : "#eee",
                  color: tokens.muted,
                  whiteSpace: "nowrap",
                }}>
                  {hit.tag || PAGE_TAG[hit.page] || hit.page}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
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
    </div>
  );
}
