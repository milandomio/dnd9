import { Fragment, useEffect, useState } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { SearchOutlined } from '@ant-design/icons';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion, useSeasonVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { dataUrl } from '../utils/dataUrl';
import QuestSearchBar from '../components/QuestSearchBar';
import type { QuestSearchResult } from '../components/QuestSearchBar';
import type { NPCEntry } from '../types/quest';

const RARITY_COLORS_LIGHT: Record<string, string> = {
  粗糙: '#757575',
  普通: '#1a1a1a',
  优秀: '#2e7d32',
  罕见: '#1565c0',
  史诗: '#7B1FA2',
  传奇: '#E65100',
  独特: '#F9A825',
};

const RARITY_COLORS_DARK: Record<string, string> = {
  粗糙: '#9e9e9e',
  普通: '#ffffff',
  优秀: '#4caf50',
  罕见: '#42a5f5',
  史诗: '#CE93D8',
  传奇: '#ff9800',
  独特: '#fff9c4',
};

function getRarityColor(rarity: string, dark: boolean): string {
  const map = dark ? RARITY_COLORS_DARK : RARITY_COLORS_LIGHT;
  return map[rarity] || (dark ? '#CE93D8' : '#7B1FA2');
}

function lsGet(key: string): boolean {
  try {
    return localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}

function lsSet(key: string, val: boolean) {
  try {
    localStorage.setItem(key, val ? '1' : '0');
  } catch {
    /* empty */
  }
}

const checkboxStyle: React.CSSProperties = {
  accentColor: '#4CAF50',
  cursor: 'pointer',
  margin: 0,
  flexShrink: 0,
};

const HIDDEN_QUESTS = new Set(['Id_Quest_Leathersmith_02']);

const CONTENT_TYPE_KEY: Record<string, string> = {
  Kill: 'ui.content.kill',
  Fetch: 'ui.content.collect',
  Explore: 'ui.content.explore',
  Props: 'ui.content.prop',
  UseItem: 'ui.content.use',
  Escape: 'ui.content.escape',
  Hold: 'ui.content.hold',
  Damage: 'ui.content.damage',
};

const REWARD_TYPE_KEY: Record<string, string> = {
  item: 'ui.quest_detail.item',
  exp: 'ui.quest_detail.exp',
  affinity: 'ui.quest_detail.affinity',
  random: 'ui.quest_detail.random_reward',
};

function formatRequired(
  allNpcs: NPCEntry[],
  required: string,
  translate: (key: string | undefined, fallback: string) => string
): { text: string; npcName?: string; questNum?: number } | null {
  if (!required) return null;
  const questId = required.replace('.json', '');
  for (const n of allNpcs) {
    for (const q of n.quests) {
      if (q.id === questId) {
        return {
          text: `${translate(n.translation_key, n.npc_name_display)}#${q.quest_number} ${translate(q.translation_key, q.title)}`,
          npcName: n.npc_name,
          questNum: q.quest_number,
        };
      }
    }
  }
  return { text: required };
}

export default function QuestNPCDetailPage() {
  const { npc_name } = useParams<{ npc_name: string }>();
  const { tokens, dark } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { t, ut, lang } = useLocale();

  const ssrData = useSSRData<NPCEntry[]>('quest_npc');
  const [allNpcs, setAllNpcs] = useState<NPCEntry[]>(ssrData || []);
  const [search, setSearch] = useState('');
  const [onlyFetch, setOnlyFetch] = useState(false);
  const [onlySuggested, setOnlySuggested] = useState(false);
  const dataVersion = useDataVersion();
  const seasonVersion = useSeasonVersion();

  const highlightQuestNum = (location.state as { questNumber?: number })
    ?.questNumber;
  const highlightSearchText = (location.state as { searchText?: string })
    ?.searchText;

  useEffect(() => {
    if (ssrData) return;
    fetch(dataUrl(dataVersion, '/data/json/quest_npc.json'))
      .then<NPCEntry[]>((r) => r.json())
      .then(setAllNpcs)
      .catch(console.error);
  }, [ssrData, dataVersion]);

  // Only clear quest_npc_* localStorage keys when season version changes
  useEffect(() => {
    if (!seasonVersion) return;
    const storedVer = localStorage.getItem('quest_npc_season');
    if (storedVer !== String(seasonVersion)) {
      const toRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith('quest_npc_')) toRemove.push(key);
      }
      toRemove.forEach((k) => localStorage.removeItem(k));
      localStorage.setItem('quest_npc_season', String(seasonVersion));
    }
  }, [seasonVersion]);

  const npc = allNpcs.find((n) => n.npc_name === npc_name);

  const refresh = () => setAllNpcs((prev) => [...prev]);

  // Set search text from navigation state
  useEffect(() => {
    if (highlightSearchText) setSearch(highlightSearchText);
  }, [highlightSearchText]);

  // Scroll to highlighted quest after data loads
  useEffect(() => {
    if (!highlightQuestNum) return;
    const timer = setTimeout(() => {
      document
        .querySelector(`[data-quest-num="${highlightQuestNum}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
    return () => clearTimeout(timer);
  }, [highlightQuestNum, npc?.npc_name]);

  if (!npc) {
    return (
      <div
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          textAlign: 'center',
          marginTop: 100,
          color: tokens.muted,
        }}
      >
        {ut('ui.common.loading')}
      </div>
    );
  }

  const lastAffinityQuest = npc.quests
    .filter((q) => q.rewards.some((r) => r.type_key === 'affinity'))
    .slice(-1)[0];

  const quests = npc.quests.filter((q) => {
    if (HIDDEN_QUESTS.has(q.id)) return false;
    if (onlyFetch && !q.contents.some((c) => c.type === 'Fetch')) return false;
    if (
      onlySuggested &&
      lastAffinityQuest &&
      q.quest_number > lastAffinityQuest.quest_number
    )
      return false;
    return true;
  });

  const matchedQuestNum = (() => {
    if (!search) return null;
    const s = search.toLowerCase();
    const found = npc.quests.find(
      (q) =>
        q.title.toLowerCase().includes(s) ||
        q.id.toLowerCase().includes(s) ||
        q.contents.some((c) => c.target.toLowerCase().includes(s))
    );
    return found?.quest_number ?? null;
  })();

  const npcDone = lsGet(`quest_npc_npc_${npc.npc_name}`);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${t(npc.translation_key, npc.npc_name_display)} ${ut('ui.quest_detail.task_list')}`}
          | DarkFlashNav
        </title>
        <meta
          name="description"
          content={`${t(npc.translation_key, npc.npc_name_display)} - ${ut('ui.quest_detail.task_list')}`}
        />
      </Helmet>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          borderBottom: `3px solid ${tokens.accent}`,
          paddingBottom: 15,
          marginBottom: 30,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ width: '100%' }}>
          <QuestSearchBar
            allNpcs={allNpcs}
            onSelect={(r: QuestSearchResult) => {
              if (r.npc.npc_name === npc_name) {
                setSearch(r.quest.title);
                requestAnimationFrame(() => {
                  const el = document.querySelector(
                    `[data-quest-num="${r.quest.quest_number}"]`
                  );
                  el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                });
              } else {
                navigate(`/${lang}/quest_npc/${r.npc.npc_name}`, {
                  state: {
                    questNumber: r.quest.quest_number,
                    searchText: r.quest.title,
                  },
                });
              }
            }}
          />
        </div>
        <div style={{ flex: 1, textAlign: 'center' }}>
          <h1
            style={{
              color: tokens.accent,
              margin: 0,
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'baseline',
              gap: 4,
              justifyContent: 'center',
            }}
          >
            <input
              type="checkbox"
              checked={npcDone}
              onChange={() => {
                lsSet(`quest_npc_npc_${npc.npc_name}`, !npcDone);
                refresh();
              }}
              style={{
                ...checkboxStyle,
                width: 22,
                height: 22,
                marginRight: 8,
              }}
            />
            {t(npc.translation_key, npc.npc_name_display)} -{' '}
            {ut('ui.quest_detail.task_list')}
            <span style={{ color: tokens.muted, fontSize: 14 }}>
              {ut('ui.quest_detail.tasks_count').replace(
                '{count}',
                String(quests.length)
              )}
            </span>
          </h1>
        </div>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
            fontSize: 13,
            color: tokens.muted,
          }}
        >
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            <input
              type="checkbox"
              checked={onlyFetch}
              onChange={(e) => setOnlyFetch(e.target.checked)}
              style={{ ...checkboxStyle, width: 16, height: 16 }}
            />
            {ut('ui.quest_detail.fetch_only')}
          </label>
          {lastAffinityQuest && (
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <input
                type="checkbox"
                checked={onlySuggested}
                onChange={(e) => setOnlySuggested(e.target.checked)}
                style={{ ...checkboxStyle, width: 16, height: 16 }}
              />
              {ut('ui.quest_detail.suggest_to')}
              {lastAffinityQuest.quest_number}
            </label>
          )}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: 12,
          marginBottom: 40,
        }}
      >
        {quests.map((q) => {
          const questDone = lsGet(
            `quest_npc_quest_${npc.npc_name}_${q.quest_number}`
          );

          return (
            <div
              key={q.id}
              data-quest-num={q.quest_number}
              style={{
                background:
                  q.quest_number === matchedQuestNum
                    ? dark
                      ? '#555'
                      : '#e8e8e8'
                    : tokens.card,
                border:
                  q.quest_number === matchedQuestNum
                    ? `2px solid ${tokens.accent}`
                    : questDone
                      ? '1px solid #388E3C'
                      : `1px solid ${tokens.border}`,
                borderRadius: 8,
                padding: questDone ? '4px 14px' : 14,
                boxShadow:
                  q.quest_number === matchedQuestNum
                    ? '0 0 12px rgba(100,180,255,0.4)'
                    : '0 2px 8px rgba(0,0,0,0.3)',
                transition: 'box-shadow 0.3s, transform 0.3s, opacity 0.2s',
                opacity: questDone ? 0.5 : 1,
                overflow: 'hidden',
                minWidth: 0,
                height: questDone ? 32 : 'auto',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.borderColor = tokens.accent;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.borderColor = questDone
                  ? '#388E3C'
                  : tokens.border;
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 4,
                }}
              >
                <input
                  type="checkbox"
                  checked={questDone}
                  onChange={() => {
                    lsSet(
                      `quest_npc_quest_${npc.npc_name}_${q.quest_number}`,
                      !questDone
                    );
                    refresh();
                  }}
                  style={{ ...checkboxStyle, width: 22, height: 22 }}
                />
                <span
                  style={{
                    fontSize: 18,
                    fontWeight: 'bold',
                    color: tokens.text,
                    textDecoration: questDone ? 'line-through' : 'none',
                  }}
                >
                  #{q.quest_number} {t(q.translation_key, q.title)}
                </span>
              </div>

              {!questDone && (
                <>
                  {q.contents.length > 0 &&
                    (() => {
                      const hasLoot = q.contents.some((c) => c.loot_state);
                      const hasRarity = q.contents.some((c) => c.rarity);
                      return (
                        <div
                          style={{
                            background:
                              'linear-gradient(135deg, rgba(33,150,243,0.08), rgba(33,150,243,0.04))',
                            border: '1px solid rgba(33,150,243,0.2)',
                            padding: 8,
                            borderRadius: 6,
                            marginBottom: 8,
                          }}
                        >
                          <div
                            style={{
                              fontSize: 12,
                              color: tokens.accent,
                              fontWeight: 'bold',
                              marginBottom: 4,
                            }}
                          >
                            {ut('ui.quest_detail.objective')}
                          </div>
                          <div
                            style={{
                              display: 'grid',
                              gridTemplateColumns: `auto minmax(0, 1fr)${hasLoot ? ' auto' : ''}${hasRarity ? ' auto' : ''} 5em`,
                              fontSize: 14,
                            }}
                          >
                            <div
                              style={{
                                display: 'contents',
                                color: tokens.muted,
                                fontSize: 13,
                                fontWeight: 'bold',
                              }}
                            >
                              <span
                                style={{
                                  padding: '4px 8px',
                                  borderBottom: `1px solid ${tokens.border}`,
                                }}
                              >
                                {ut('ui.quest_detail.type')}
                              </span>
                              <span
                                style={{
                                  padding: '4px 8px',
                                  borderBottom: `1px solid ${tokens.border}`,
                                }}
                              >
                                {ut('ui.quest_detail.target')} /{' '}
                                {ut('ui.quest_detail.target_map')}
                              </span>
                              {hasLoot && (
                                <span
                                  style={{
                                    padding: '4px 8px',
                                    borderBottom: `1px solid ${tokens.border}`,
                                  }}
                                >
                                  {ut('ui.quest_detail.loot')}
                                </span>
                              )}
                              {hasRarity && (
                                <span
                                  style={{
                                    padding: '4px 8px',
                                    borderBottom: `1px solid ${tokens.border}`,
                                  }}
                                >
                                  {ut('ui.quest_detail.rarity')}
                                </span>
                              )}
                            </div>
                            <div
                              style={{
                                padding: '4px 8px',
                                borderBottom: `1px solid ${tokens.border}`,
                                color: tokens.muted,
                                fontSize: 13,
                                fontWeight: 'bold',
                                textAlign: 'center',
                              }}
                            >
                              {ut('ui.quest_detail.count')}
                            </div>
                            {q.contents.map((c, i) => {
                              const contentKey = `quest_npc_content_${npc.npc_name}_${q.quest_number}_${i}`;
                              const contentDone = lsGet(contentKey);
                              const mergeRarityIntoTarget =
                                !c.dungeon_type && Boolean(c.rarity);
                              const rowStyle = {
                                borderBottom: dark
                                  ? '1px solid rgba(255,255,255,0.06)'
                                  : '1px solid rgba(0,0,0,0.08)',
                                opacity: contentDone ? 0.4 : 1,
                                textDecoration: contentDone
                                  ? 'line-through'
                                  : 'none',
                              };
                              return (
                                <Fragment key={i}>
                                  <div
                                    style={{
                                      display: 'contents',
                                    }}
                                  >
                                    <span
                                      style={{
                                        ...rowStyle,
                                        color: dark ? '#ccc' : '#555',
                                        whiteSpace: 'nowrap',
                                        padding: '6px 8px',
                                      }}
                                    >
                                      {ut(CONTENT_TYPE_KEY[c.type] || c.type)}
                                    </span>
                                    <div
                                      style={{
                                        ...rowStyle,
                                        color: tokens.text,
                                        minWidth: 0,
                                        whiteSpace: 'nowrap',
                                        padding: '6px 8px',
                                        position: 'relative',
                                        zIndex: 1,
                                      }}
                                    >
                                      <input
                                        type="checkbox"
                                        checked={contentDone}
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          lsSet(contentKey, !contentDone);
                                          refresh();
                                        }}
                                        onChange={() => {}}
                                        style={{
                                          ...checkboxStyle,
                                          width: 16,
                                          height: 16,
                                          marginRight: 4,
                                        }}
                                      />
                                      {t(c.translation_key, c.target)}
                                      <SearchOutlined
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          navigate(location.pathname, {
                                            state: {
                                              searchQuery: t(
                                                c.translation_key,
                                                c.target
                                              ),
                                            },
                                          });
                                        }}
                                        title={ut('ui.search.search')}
                                        style={{
                                          marginLeft: 6,
                                          cursor: 'pointer',
                                          fontSize: 13,
                                          color: tokens.muted,
                                          transition: 'color 0.2s',
                                          verticalAlign: 'middle',
                                        }}
                                        onMouseEnter={(e) => {
                                          e.currentTarget.style.color =
                                            tokens.accent;
                                        }}
                                        onMouseLeave={(e) => {
                                          e.currentTarget.style.color =
                                            tokens.muted;
                                        }}
                                      />
                                      {c.dungeon_type && (
                                        <div
                                          style={{
                                            color: dark ? '#42a5f5' : '#1565c0',
                                            fontSize: 12,
                                          }}
                                        >
                                          {t(
                                            c.dungeon_translation_key,
                                            c.dungeon_type || ''
                                          )}
                                        </div>
                                      )}
                                      {mergeRarityIntoTarget && (
                                        <div
                                          style={{
                                            color: getRarityColor(
                                              c.rarity || '',
                                              dark
                                            ),
                                            fontSize: 12,
                                          }}
                                        >
                                          {t(
                                            c.rarity_translation_key,
                                            c.rarity || ''
                                          )}
                                        </div>
                                      )}
                                    </div>
                                    {hasLoot && (
                                      <span
                                        style={{
                                          ...rowStyle,
                                          color: dark ? '#FFB74D' : '#E65100',
                                          fontSize: 12,
                                          padding: '6px 8px',
                                          textAlign: 'center',
                                          fontWeight: 900,
                                        }}
                                      >
                                        {c.loot_state ? '✓' : ''}
                                      </span>
                                    )}
                                    {hasRarity && !mergeRarityIntoTarget && (
                                      <span
                                        style={{
                                          ...rowStyle,
                                          color: getRarityColor(
                                            c.rarity || '',
                                            dark
                                          ),
                                          fontSize: 12,
                                          whiteSpace: 'nowrap',
                                          padding: '6px 8px',
                                        }}
                                      >
                                        {t(
                                          c.rarity_translation_key,
                                          c.rarity || ''
                                        )}
                                      </span>
                                    )}
                                    {hasRarity && mergeRarityIntoTarget && (
                                      <span
                                        style={{
                                          ...rowStyle,
                                          padding: '6px 8px',
                                        }}
                                      />
                                    )}
                                  </div>
                                  <div
                                    style={{
                                      ...rowStyle,
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      padding: '6px 8px',
                                      color: dark ? '#ccc' : '#555',
                                      whiteSpace: 'nowrap',
                                      position: 'relative',
                                      zIndex: 0,
                                    }}
                                  >
                                    {c.count}
                                  </div>
                                </Fragment>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })()}

                  {q.rewards.length > 0 && (
                    <div
                      style={{
                        background:
                          'linear-gradient(135deg, rgba(76,175,80,0.08), rgba(76,175,80,0.04))',
                        border: '1px solid rgba(76,175,80,0.2)',
                        padding: 8,
                        borderRadius: 6,
                        marginBottom: 8,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 12,
                          color: tokens.accent,
                          fontWeight: 'bold',
                          marginBottom: 4,
                        }}
                      >
                        {ut('ui.quest_detail.reward')}
                      </div>
                      <table
                        style={{
                          width: '100%',
                          borderCollapse: 'collapse',
                          fontSize: 14,
                          tableLayout: 'auto',
                          overflowWrap: 'anywhere',
                        }}
                      >
                        <thead>
                          <tr
                            style={{
                              borderBottom: `1px solid ${tokens.border}`,
                            }}
                          >
                            <th
                              style={{
                                textAlign: 'left',
                                padding: '4px 8px',
                                color: tokens.muted,
                                fontSize: 13,
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {ut('ui.quest_detail.type')}
                            </th>
                            <th
                              style={{
                                textAlign: 'left',
                                padding: '4px 8px',
                                color: tokens.muted,
                                fontSize: 13,
                              }}
                            >
                              {ut('ui.quest_detail.item')}
                            </th>
                            <th
                              style={{
                                textAlign: 'center',
                                padding: '4px 8px',
                                color: tokens.muted,
                                fontSize: 13,
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {ut('ui.quest_detail.count')}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {/* 好感度 → 固定第一行 */}
                          {q.rewards
                            .filter((r) => r.type_key === 'affinity')
                            .map((r, ri) => (
                              <tr
                                key={`aff-${ri}`}
                                style={{
                                  borderBottom: dark
                                    ? '1px solid rgba(255,255,255,0.06)'
                                    : '1px solid rgba(0,0,0,0.08)',
                                  background: 'rgba(255,100,100,0.1)',
                                }}
                              >
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: dark ? '#ccc' : '#555',
                                    textAlign: 'center',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {ut(
                                    REWARD_TYPE_KEY[r.type_key] || r.type_key
                                  )}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: tokens.text,
                                  }}
                                >
                                  {t(r.translation_key, r.name)}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: dark ? '#ccc' : '#555',
                                    textAlign: 'center',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {r.count}
                                </td>
                              </tr>
                            ))}
                          {/* 普通奖励（排除好感度、经验值、金币） */}
                          {q.rewards
                            .filter(
                              (r) =>
                                r.type_key !== 'affinity' &&
                                r.type_key !== 'exp' &&
                                !(r.type_key === 'item' && r.name === '金币')
                            )
                            .map((r, ri) => (
                              <tr
                                key={`item-${ri}`}
                                style={{
                                  borderBottom: dark
                                    ? '1px solid rgba(255,255,255,0.06)'
                                    : '1px solid rgba(0,0,0,0.08)',
                                }}
                              >
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: dark ? '#ccc' : '#555',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {ut(
                                    REWARD_TYPE_KEY[r.type_key] || r.type_key
                                  )}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: tokens.text,
                                  }}
                                >
                                  {t(r.translation_key, r.name)}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: dark ? '#ccc' : '#555',
                                    textAlign: 'center',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {r.count}
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                      {/* 金币 + 经验值 → 固定最后一行，4列 */}
                      {(() => {
                        const expReward = q.rewards.find(
                          (r) => r.type_key === 'exp'
                        );
                        const goldReward = q.rewards.find(
                          (r) => r.type_key === 'item' && r.name === '金币'
                        );
                        if (!expReward && !goldReward) return null;
                        return (
                          <div
                            style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(4, 1fr)',
                              borderTop: `1px solid ${tokens.border}`,
                              marginTop: 4,
                              fontSize: 14,
                            }}
                          >
                            <div
                              style={{
                                padding: '3px 8px',
                                color: dark ? '#FFD54F' : '#F57F17',
                              }}
                            >
                              {ut('ui.quest_detail.gold')}
                            </div>
                            <div
                              style={{
                                padding: '3px 8px',
                                color: dark ? '#FFD54F' : '#F57F17',
                              }}
                            >
                              {goldReward?.count ?? ''}
                            </div>
                            <div
                              style={{
                                padding: '3px 8px',
                                color: dark ? '#4fc3f7' : '#0277BD',
                              }}
                            >
                              {ut('ui.quest_detail.exp')}
                            </div>
                            <div
                              style={{
                                padding: '3px 8px',
                                color: dark ? '#4fc3f7' : '#0277BD',
                              }}
                            >
                              {expReward?.count ?? ''}
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}

                  {q.required &&
                    (() => {
                      const req = formatRequired(allNpcs, q.required, t);
                      if (!req) return null;
                      const isPrevSameNpc =
                        req.npcName === npc.npc_name &&
                        req.questNum === q.quest_number - 1;
                      return (
                        <div
                          style={{
                            color: dark ? '#ccc' : '#555',
                            fontSize: 13,
                            marginTop: 6,
                          }}
                        >
                          <span style={{ fontWeight: 'bold' }}>
                            {ut('ui.quest_detail.prereq')}
                          </span>
                          {isPrevSameNpc ? (
                            <span>{ut('ui.quest_detail.prev_quest')}</span>
                          ) : req.npcName ? (
                            <Link
                              to={`/${lang}/quest_npc/${req.npcName}`}
                              style={{
                                color: tokens.accent,
                                textDecoration: 'none',
                              }}
                            >
                              【{req.text}】
                            </Link>
                          ) : (
                            <span>【{req.text}】</span>
                          )}
                        </div>
                      );
                    })()}
                </>
              )}
            </div>
          );
        })}
      </div>

      {quests.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            color: tokens.muted,
            fontSize: 16,
            marginTop: 40,
          }}
        >
          {search
            ? ut('ui.quest_detail.no_match')
            : ut('ui.quest_detail.no_tasks')}
        </div>
      )}
    </div>
  );
}
