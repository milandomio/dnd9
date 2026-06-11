import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';

interface QuestContent {
  type: string;
  target: string;
  count: number;
  loot_state?: string;
  rarity?: string;
}

interface QuestReward {
  type: string;
  name: string;
  type_key: string;
  count: number;
}

interface NPCQuest {
  id: string;
  title: string;
  quest_number: number;
  contents: QuestContent[];
  rewards: QuestReward[];
  required: string;
}

interface NPCEntry {
  npc_name: string;
  npc_name_display: string;
  quest_count: number;
  category: string;
  quests: NPCQuest[];
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
  const { tokens } = useTheme();

  const ssrData = useSSRData<NPCEntry[]>('quest_npc');
  const [allNpcs, setAllNpcs] = useState<NPCEntry[]>(ssrData || []);
  const [search, setSearch] = useState('');
  const dataVersion = useDataVersion();

  useEffect(() => {
    if (ssrData) return;
    fetch(`./data/json/quest_npc.json?v=${dataVersion}`)
      .then<NPCEntry[]>((r) => r.json())
      .then(setAllNpcs)
      .catch(console.error);
  }, [ssrData]);

  const npc = allNpcs.find((n) => n.npc_name === npc_name);

  const refresh = () => setAllNpcs((prev) => [...prev]);

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

  const quests = npc.quests.filter((q) => {
    if (HIDDEN_QUESTS.has(q.id)) return false;
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

      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          borderBottom: `3px solid ${tokens.accent}`,
          paddingBottom: 15,
          marginBottom: 30,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
        }}
      >
        <input
          type="checkbox"
          checked={npcDone}
          onChange={() => {
            lsSet(`quest_npc_npc_${npc.npc_name}`, !npcDone);
            refresh();
          }}
          style={{ ...checkboxStyle, width: 22, height: 22 }}
        />
        {npc.npc_name_display} - 任务列表
        <span style={{ color: tokens.muted, fontSize: 16 }}>
          {quests.length} 个任务
        </span>
      </h1>

      <div style={{ textAlign: 'center', marginBottom: 20 }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索任务..."
          style={{
            width: 300,
            maxWidth: '80%',
            padding: '10px 15px',
            fontSize: 14,
            border: `2px solid ${tokens.border}`,
            borderRadius: 4,
            background: tokens.surface,
            color: tokens.text,
            outline: 'none',
          }}
          onFocus={(e) => (e.target.style.borderColor = tokens.accent)}
          onBlur={(e) => (e.target.style.borderColor = tokens.border)}
        />
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
              style={{
                background: tokens.card,
                border: questDone
                  ? '1px solid #388E3C'
                  : `1px solid ${tokens.border}`,
                borderRadius: 8,
                padding: 14,
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                transition: 'box-shadow 0.3s, transform 0.3s, opacity 0.2s',
                opacity: questDone ? 0.5 : 1,
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
                                color: '#aaa',
                                fontSize: 13,
                              }}
                            >
                              类型
                            </th>
                            <th
                              style={{
                                textAlign: 'left',
                                padding: '4px 8px',
                                color: '#aaa',
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
                                  color: '#aaa',
                                  fontSize: 13,
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
                                  color: '#aaa',
                                  fontSize: 13,
                                }}
                              >
                                稀有度
                              </th>
                            )}
                            <th
                              style={{
                                textAlign: 'left',
                                padding: '4px 8px',
                                color: '#aaa',
                                fontSize: 13,
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
                                  borderBottom:
                                    '1px solid rgba(255,255,255,0.06)',
                                  opacity: contentDone ? 0.4 : 1,
                                  textDecoration: contentDone
                                    ? 'line-through'
                                    : 'none',
                                }}
                              >
                                <td
                                  style={{ padding: '3px 8px', color: '#ccc' }}
                                >
                                  {CONTENT_TYPE_LABEL[c.type] || c.type}
                                </td>
                                <td
                                  style={{ padding: '3px 8px', color: '#fff' }}
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
                                </td>
                                {hasLoot && (
                                  <td
                                    style={{
                                      padding: '3px 8px',
                                      color: '#FFB74D',
                                      fontSize: 12,
                                    }}
                                  >
                                    {c.loot_state || ''}
                                  </td>
                                )}
                                {hasRarity && (
                                  <td
                                    style={{
                                      padding: '3px 8px',
                                      color: '#CE93D8',
                                      fontSize: 12,
                                    }}
                                  >
                                    {c.rarity || ''}
                                  </td>
                                )}
                                <td
                                  style={{ padding: '3px 8px', color: '#ccc' }}
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
                    }}
                  >
                    <thead>
                      <tr
                        style={{ borderBottom: `1px solid ${tokens.border}` }}
                      >
                        <th
                          style={{
                            textAlign: 'left',
                            padding: '4px 8px',
                            color: '#aaa',
                            fontSize: 13,
                          }}
                        >
                          类型
                        </th>
                        <th
                          style={{
                            textAlign: 'left',
                            padding: '4px 8px',
                            color: '#aaa',
                            fontSize: 13,
                          }}
                        >
                          物品
                        </th>
                        <th
                          style={{
                            textAlign: 'left',
                            padding: '4px 8px',
                            color: '#aaa',
                            fontSize: 13,
                          }}
                        >
                          数量
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {q.rewards.map((r, ri) => {
                        const isAffinity = r.type_key === 'affinity';
                        return (
                          <tr
                            key={ri}
                            style={{
                              borderBottom: '1px solid rgba(255,255,255,0.06)',
                              background: isAffinity
                                ? 'rgba(255,100,100,0.1)'
                                : undefined,
                            }}
                          >
                            <td style={{ padding: '3px 8px', color: '#ccc' }}>
                              {REWARD_TYPE_LABEL[r.type_key] || r.type_key}
                            </td>
                            <td style={{ padding: '3px 8px', color: '#fff' }}>
                              {r.name}
                            </td>
                            <td style={{ padding: '3px 8px', color: '#ccc' }}>
                              {r.count}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
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
                    <div style={{ color: '#ccc', fontSize: 13, marginTop: 6 }}>
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
