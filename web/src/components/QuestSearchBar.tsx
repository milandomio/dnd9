import { useState, useEffect, useRef, useMemo } from 'react';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import type { NPCQuest, NPCEntry } from '../types/quest';

export interface QuestSearchResult {
  quest: NPCQuest;
  npc: NPCEntry;
  matchField: 'title' | 'id' | 'target';
  matchTarget?: string;
  matchTargetTranslationKey?: string;
}

interface QuestSearchBarProps {
  allNpcs: NPCEntry[];
  onSelect: (result: QuestSearchResult) => void;
  query?: string;
  onQueryChange?: (query: string) => void;
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
  query,
  onQueryChange,
  placeholder,
}: QuestSearchBarProps) {
  const [internalQuery, setInternalQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const { dark, tokens } = useTheme();
  const { t, ut, dict } = useLocale();
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const activeQuery = query ?? internalQuery;

  const setQuery = (value: string) => {
    setInternalQuery(value);
    onQueryChange?.(value);
  };

  // Rebuild when the entity locale loads so queries match the displayed language.
  const flatIndex = useMemo(() => {
    const entries: FlatEntry[] = [];
    for (const npc of allNpcs) {
      for (const quest of npc.quests) {
        if (HIDDEN_QUESTS.has(quest.id)) continue;
        entries.push({
          quest,
          npc,
          titleLower: (
            dict?.[quest.translation_key] ?? quest.title
          ).toLowerCase(),
          idLower: quest.id.toLowerCase(),
          targetsLower: quest.contents.map((content) =>
            (
              dict?.[content.translation_key ?? ''] ?? content.target
            ).toLowerCase()
          ),
        });
      }
    }
    return entries;
  }, [allNpcs, dict]);

  // Filter on query change
  const results = useMemo(() => {
    const q = activeQuery.trim().toLowerCase();
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
            matchTargetTranslationKey:
              entry.quest.contents[idx].translation_key,
          });
        }
      }
      if (hits.length >= 80) break;
    }
    return hits;
  }, [activeQuery, flatIndex]);

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
      style={{ position: 'relative', width: 320, flexShrink: 0 }}
    >
      <input
        ref={inputRef}
        type="text"
        value={activeQuery}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (results.length > 0) setShowDropdown(true);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? ut('ui.search.placeholder')}
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
                #{hit.quest.quest_number}{' '}
                {t(hit.quest.translation_key, hit.quest.title)}
                {hit.matchField === 'target' && hit.matchTarget && (
                  <span
                    style={{
                      color: tokens.muted,
                      marginLeft: 6,
                      fontSize: 12,
                    }}
                  >
                    ({t(hit.matchTargetTranslationKey, hit.matchTarget)})
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
                {t(hit.npc.translation_key, hit.npc.npc_name_display)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
