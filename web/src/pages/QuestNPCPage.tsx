import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import QuestSearchBar from '../components/QuestSearchBar';
import type { QuestSearchResult } from '../components/QuestSearchBar';
import type { NPCEntry } from '../types/quest';

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

const CATEGORY_ORDER = ['装备NPC', '优选NPC', '可用NPC', '不推荐NPC'];

const checkboxStyle: React.CSSProperties = {
  accentColor: '#4CAF50',
  cursor: 'pointer',
  margin: 0,
  flexShrink: 0,
};

export default function QuestNPCPage() {
  const ssrData = useSSRData<NPCEntry[]>('quest_npc');
  const [data, setData] = useState<NPCEntry[]>(ssrData || []);
  const dataVersion = useDataVersion();
  const { tokens } = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    if (ssrData) return;
    fetch(`./data/json/quest_npc.json?v=${dataVersion}`)
      .then<NPCEntry[]>((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, [ssrData]);

  const grouped = new Map<string, NPCEntry[]>();
  for (const npc of data) {
    const cat = npc.category || '可用NPC';
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push(npc);
  }

  const sortedGroups = [...grouped.entries()]
    .sort(([a], [b]) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b))
    .map(
      ([cat, npcs]) =>
        [
          cat,
          npcs.sort((a, b) =>
            a.npc_name_display.localeCompare(b.npc_name_display, 'zh-CN')
          ),
        ] as const
    );

  const refresh = () => setData((prev) => [...prev]);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>任务NPC表 | DarkFindV5游戏导航</title>
        <meta
          name="description"
          content="NPC任务详情查询——查看各NPC的任务、奖励、需求。"
        />
      </Helmet>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          marginBottom: 20,
        }}
      >
        <QuestSearchBar
          allNpcs={data}
          onSelect={(r: QuestSearchResult) =>
            navigate(`/quest_npc/${r.npc.npc_name}`, {
              state: { questNumber: r.quest.quest_number },
            })
          }
        />
        <div style={{ flex: 1, textAlign: 'center' }}>
          <h1
            style={{
              color: tokens.accent,
              fontSize: 36,
              margin: 0,
            }}
          >
            【任务NPC表】NPC任务详情
          </h1>
          <div
            style={{
              color: tokens.muted,
              fontSize: 14,
              marginTop: 4,
            }}
          >
            共 {data.length} 个活跃NPC
          </div>
        </div>
      </div>
      {sortedGroups.map(([category, npcs]) => (
        <div key={category}>
          <div
            style={{
              fontSize: 22,
              fontWeight: 'bold',
              color: '#FFC107',
              padding: '5px 0',
              borderBottom: '2px solid #FFC107',
              marginBottom: 12,
              marginTop: 24,
            }}
          >
            {category} ({npcs.length})
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 12,
              marginBottom: 8,
            }}
          >
            {npcs.map((npc) => {
              const npcDone = lsGet(`quest_npc_npc_${npc.npc_name}`);
              return (
                <div
                  key={npc.npc_name}
                  style={{
                    background: tokens.card,
                    border: npcDone
                      ? '1px solid #388E3C'
                      : `1px solid ${tokens.border}`,
                    borderRadius: 8,
                    opacity: npcDone ? 0.5 : 1,
                    transition: 'opacity 0.2s',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: 20,
                      gap: 10,
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
                        flexShrink: 0,
                      }}
                    />
                    <Link
                      to={`/quest_npc/${npc.npc_name}`}
                      style={{
                        flex: 1,
                        minWidth: 0,
                        textDecoration: 'none',
                        color: tokens.text,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 18,
                          fontWeight: 'bold',
                          color: tokens.accent,
                          textDecoration: npcDone ? 'line-through' : 'none',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {npc.npc_name_display}
                        <span
                          style={{
                            fontSize: 13,
                            color: tokens.muted,
                            fontWeight: 'normal',
                            marginLeft: 8,
                          }}
                        >
                          {npc.quest_count} 个任务
                        </span>
                      </div>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
