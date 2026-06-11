import { useState, useEffect, useRef, useMemo } from 'react';
import { useTheme } from '../hooks/useTheme';
import type { NPCQuest, NPCEntry } from '../types/quest';

export interface QuestSearchResult {
  quest: NPCQuest;
  npc: NPCEntry;
  matchField: 'title' | 'id' | 'target';
  matchTarget?: string;
}

interface QuestSearchBarProps {
  allNpcs: NPCEntry[];
  onSelect: (result: QuestSearchResult) => void;
  placeholder?: string;
}

const HIDDEN_QUESTS = new Set(['Id_Quest_Leathersmith_02']);

interface FlatEntry {
  quest: NPCQuest;
  npc: NPCEntry;
  titleLower: string;
  idLower: string;
  targetsLower: string[];
}

export default function QuestSearchBar({
  allNpcs,
  onSelect,
  placeholder = '搜索任务标题 / 目标物品...',
}: QuestSearchBarProps) {
  const [query, setQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const { dark, tokens } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-build flat search index (once per allNpcs change)
  const flatIndex = useMemo(() => {
    const entries: FlatEntry[] = [];
    for (const npc of allNpcs) {
      for (const quest of npc.quests) {
        if (HIDDEN_QUESTS.has(quest.id)) continue;
        entries.push({
          quest,
          npc,
          titleLower: quest.title.toLowerCase(),
          idLower: quest.id.toLowerCase(),
          targetsLower: quest.contents.map((c) => c.target.toLowerCase()),
        });
      }
    }
    return entries;
  }, [allNpcs]);

  // Filter on query change
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const hits: QuestSearchResult[] = [];
    for (const entry of flatIndex) {
      if (entry.titleLower.includes(q)) {
        hits.push({ quest: entry.quest, npc: entry.npc, matchField: 'title' });
      } else if (entry.idLower.includes(q)) {
        hits.push({ quest: entry.quest, npc: entry.npc, matchField: 'id' });
      } else {
        const idx = entry.targetsLower.findIndex((t) => t.includes(q));
        if (idx >= 0) {
          hits.push({
            quest: entry.quest,
            npc: entry.npc,
            matchField: 'target',
            matchTarget: entry.quest.contents[idx].target,
          });
        }
      }
      if (hits.length >= 80) break;
    }
    return hits;
  }, [query, flatIndex]);

  useEffect(() => {
    setShowDropdown(results.length > 0);
    setSelectedIdx(-1);
  }, [results]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      if (selectedIdx >= 0 && results[selectedIdx]) {
        handleSelect(results[selectedIdx]);
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  };

  const handleSelect = (result: QuestSearchResult) => {
    setQuery('');
    setShowDropdown(false);
    onSelect(result);
  };

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', maxWidth: 400, margin: '0 auto 20px' }}
    >
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (results.length > 0) setShowDropdown(true);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        style={{
          width: '100%',
          padding: '10px 15px',
          fontSize: 14,
          border: `2px solid ${tokens.border}`,
          borderRadius: 6,
          background: tokens.surface,
          color: tokens.text,
          outline: 'none',
        }}
      />
      {showDropdown && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            background: dark ? '#2c2c2c' : '#fff',
            border: `1px solid ${tokens.border}`,
            borderRadius: 6,
            maxHeight: 400,
            overflowY: 'auto',
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          {results.map((hit, i) => (
            <div
              key={`${hit.npc.npc_name}::${hit.quest.id}`}
              onClick={() => handleSelect(hit)}
              onMouseEnter={() => setSelectedIdx(i)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background:
                  i === selectedIdx
                    ? dark
                      ? '#444'
                      : '#e6f4ff'
                    : 'transparent',
                transition: 'background 0.1s',
              }}
            >
              <span style={{ color: tokens.text, fontSize: 14 }}>
                #{hit.quest.quest_number} {hit.quest.title}
                {hit.matchField === 'target' && hit.matchTarget && (
                  <span
                    style={{
                      color: tokens.muted,
                      marginLeft: 6,
                      fontSize: 12,
                    }}
                  >
                    ({hit.matchTarget})
                  </span>
                )}
              </span>
              <span
                style={{
                  fontSize: 11,
                  padding: '1px 6px',
                  borderRadius: 3,
                  background: dark ? '#555' : '#eee',
                  color: tokens.muted,
                  whiteSpace: 'nowrap',
                  marginLeft: 8,
                  flexShrink: 0,
                }}
              >
                {hit.npc.npc_name_display}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
