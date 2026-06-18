import { useEffect, useState, useRef } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { SearchOutlined } from '@ant-design/icons';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
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

const CONTENT_TYPE_LABEL: Record<string, string> = {
  Kill: '击杀',
  Fetch: '收集',
  Explore: '探索',
  Props: '道具',
  UseItem: '使用',
  Escape: '逃生',
  Hold: '坚守',
  Damage: '伤害',
};

const REWARD_TYPE_LABEL: Record<string, string> = {
  item: '物品',
  exp: '经验值',
  affinity: '好感度',
  random: '随机奖励',
};

function formatRequired(
  allNpcs: NPCEntry[],
  required: string
): { text: string; npcName?: string; questNum?: number } | null {
  if (!required) return null;
  const questId = required.replace('.json', '');
  for (const n of allNpcs) {
    for (const q of n.quests) {
      if (q.id === questId) {
        return {
          text: `${n.npc_name_display}#${q.quest_number} ${q.title}`,
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
  const scrollToRef = useRef<HTMLDivElement>(null);

  const ssrData = useSSRData<NPCEntry[]>('quest_npc');
  const [allNpcs, setAllNpcs] = useState<NPCEntry[]>(ssrData || []);
  const [search, setSearch] = useState('');
  const [onlyFetch, setOnlyFetch] = useState(false);
  const [onlySuggested, setOnlySuggested] = useState(false);
  const dataVersion = useDataVersion();

  const highlightQuestNum = (location.state as { questNumber?: number })
    ?.questNumber;

  useEffect(() => {
    if (ssrData) return;
    fetch(`/data/json/quest_npc.json?v=${dataVersion}`)
      .then<NPCEntry[]>((r) => r.json())
      .then(setAllNpcs)
      .catch(console.error);
  }, [ssrData]);

  const npc = allNpcs.find((n) => n.npc_name === npc_name);

  const refresh = () => setAllNpcs((prev) => [...prev]);

  // Scroll to highlighted quest after data loads
  useEffect(() => {
    if (highlightQuestNum && scrollToRef.current) {
      scrollToRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [highlightQuestNum, allNpcs]);

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
        加载中...
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
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      q.title.toLowerCase().includes(s) ||
      q.id.toLowerCase().includes(s) ||
      q.contents.some((c) => c.target.toLowerCase().includes(s))
    );
  });

  const npcDone = lsGet(`quest_npc_npc_${npc.npc_name}`);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>{npc.npc_name_display} - 任务列表 | DarkFindV5游戏导航</title>
        <meta
          name="description"
          content={`${npc.npc_name_display}的任务详情——查看所有任务、奖励、需求。`}
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
        }}
      >
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
              navigate(`/quest_npc/${r.npc.npc_name}`, {
                state: { questNumber: r.quest.quest_number },
              });
            }
          }}
        />
        <div style={{ flex: 1, textAlign: 'center' }}>
          <h1 style={{ color: tokens.accent, margin: 0 }}>
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
            {npc.npc_name_display} - 任务列表
            <span style={{ color: tokens.muted, fontSize: 14, marginLeft: 8 }}>
              {quests.length}个任务
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
            仅显示收集任务
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
              建议完成至#{lastAffinityQuest.quest_number}
            </label>
          )}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
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
              ref={
                q.quest_number === highlightQuestNum ? scrollToRef : undefined
              }
              data-quest-num={q.quest_number}
              style={{
                background: tokens.card,
                border: questDone
                  ? '1px solid #388E3C'
                  : `1px solid ${tokens.border}`,
                borderRadius: 8,
                padding: questDone ? '4px 14px' : 14,
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
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
                  #{q.quest_number} {q.title}
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
                            任务目标
                          </div>
                          <table
                            style={{
                              width: '100%',
                              borderCollapse: 'collapse',
                              fontSize: 14,
                              tableLayout: 'fixed',
                              wordBreak: 'break-word',
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
                                    width: '2em',
                                  }}
                                >
                                  类型
                                </th>
                                <th
                                  style={{
                                    textAlign: 'left',
                                    padding: '4px 8px',
                                    color: tokens.muted,
                                    fontSize: 13,
                                  }}
                                >
                                  目标
                                </th>
                                {hasLoot && (
                                  <th
                                    style={{
                                      textAlign: 'left',
                                      padding: '4px 8px',
                                      color: tokens.muted,
                                      fontSize: 13,
                                      whiteSpace: 'nowrap',
                                      width: '3em',
                                    }}
                                  >
                                    战利品
                                  </th>
                                )}
                                {hasRarity && (
                                  <th
                                    style={{
                                      textAlign: 'left',
                                      padding: '4px 8px',
                                      color: tokens.muted,
                                      fontSize: 13,
                                      whiteSpace: 'nowrap',
                                      width: '3em',
                                    }}
                                  >
                                    稀有度
                                  </th>
                                )}
                                <th
                                  style={{
                                    textAlign: 'left',
                                    padding: '4px 8px',
                                    color: tokens.muted,
                                    fontSize: 13,
                                    whiteSpace: 'nowrap',
                                    width: '2em',
                                  }}
                                >
                                  数量
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {q.contents.map((c, i) => {
                                const contentKey = `quest_npc_content_${npc.npc_name}_${q.quest_number}_${i}`;
                                const contentDone = lsGet(contentKey);
                                return (
                                  <tr
                                    key={i}
                                    style={{
                                      borderBottom: dark
                                        ? '1px solid rgba(255,255,255,0.06)'
                                        : '1px solid rgba(0,0,0,0.08)',
                                      opacity: contentDone ? 0.4 : 1,
                                      textDecoration: contentDone
                                        ? 'line-through'
                                        : 'none',
                                    }}
                                  >
                                    <td
                                      style={{
                                        padding: '3px 8px',
                                        color: dark ? '#ccc' : '#555',
                                        whiteSpace: 'nowrap',
                                      }}
                                    >
                                      {CONTENT_TYPE_LABEL[c.type] || c.type}
                                    </td>
                                    <td
                                      style={{
                                        padding: '3px 8px',
                                        color: tokens.text,
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
                                      {c.target}
                                      <SearchOutlined
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          navigate(location.pathname, {
                                            state: { searchQuery: c.target },
                                          });
                                        }}
                                        title={`搜索"${c.target}"`}
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
                                    </td>
                                    {hasLoot && (
                                      <td
                                        style={{
                                          padding: '3px 8px',
                                          color: dark ? '#FFB74D' : '#E65100',
                                          fontSize: 12,
                                          whiteSpace: 'nowrap',
                                        }}
                                      >
                                        {c.loot_state || ''}
                                      </td>
                                    )}
                                    {hasRarity && (
                                      <td
                                        style={{
                                          padding: '3px 8px',
                                          color: getRarityColor(
                                            c.rarity || '',
                                            dark
                                          ),
                                          fontSize: 12,
                                          whiteSpace: 'nowrap',
                                        }}
                                      >
                                        {c.rarity || ''}
                                      </td>
                                    )}
                                    <td
                                      style={{
                                        padding: '3px 8px',
                                        color: dark ? '#ccc' : '#555',
                                        whiteSpace: 'nowrap',
                                      }}
                                    >
                                      {c.count}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
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
                        任务奖励
                      </div>
                      <table
                        style={{
                          width: '100%',
                          borderCollapse: 'collapse',
                          fontSize: 14,
                          tableLayout: 'fixed',
                          wordBreak: 'break-word',
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
                                width: '4em',
                              }}
                            >
                              类型
                            </th>
                            <th
                              style={{
                                textAlign: 'left',
                                padding: '4px 8px',
                                color: tokens.muted,
                                fontSize: 13,
                              }}
                            >
                              物品
                            </th>
                            <th
                              style={{
                                textAlign: 'left',
                                padding: '4px 8px',
                                color: tokens.muted,
                                fontSize: 13,
                                whiteSpace: 'nowrap',
                                width: '2em',
                              }}
                            >
                              数量
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
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {REWARD_TYPE_LABEL[r.type_key] || r.type_key}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: tokens.text,
                                  }}
                                >
                                  {r.name}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: dark ? '#ccc' : '#555',
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
                                  {REWARD_TYPE_LABEL[r.type_key] || r.type_key}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: tokens.text,
                                  }}
                                >
                                  {r.name}
                                </td>
                                <td
                                  style={{
                                    padding: '3px 8px',
                                    color: dark ? '#ccc' : '#555',
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
                              金币
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
                              经验值
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
                      const req = formatRequired(allNpcs, q.required);
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
                          <span style={{ fontWeight: 'bold' }}>前置任务: </span>
                          {isPrevSameNpc ? (
                            <span>【上一个】</span>
                          ) : req.npcName ? (
                            <Link
                              to={`/quest_npc/${req.npcName}`}
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
          {search ? '没有匹配的任务' : '该NPC暂无任务'}
        </div>
      )}
    </div>
  );
}
