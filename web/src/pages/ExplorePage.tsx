import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useSSRData } from '../context/SSRDataContext';
import Disclaimer from '../components/Disclaimer';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import { useDungeonModules } from '../hooks/useDungeonModules';

interface ExploreTarget {
  name: string;
  module_name: string;
  quest_title: string;
  npc_name: string;
  npc_name_display: string;
  quest_number: number;
}

function modKey(module_name: string): string {
  return module_name.replace(/^Id_DungeonModule_/, '');
}

export default function ExplorePage() {
  const ssrData = useSSRData<ExploreTarget[]>('explore');
  const [data, setData] = useState<ExploreTarget[]>(ssrData || []);
  const { modules } = useDungeonModules();
  const dataVersion = useDataVersion();
  const { tokens, dark } = useTheme();

  useEffect(() => {
    if (ssrData) return;
    fetch('/data/json/explore.json')
      .then<ExploreTarget[]>((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, [ssrData, dataVersion]);

  const grouped = new Map<string, ExploreTarget[]>();
  for (const t of data) {
    const key = t.npc_name_display || t.npc_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(t);
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>任务探索表 | 越来越黑暗闪电指南 DarkFlashNav</title>
        <meta
          name="description"
          content={`探索目标汇总——${data.length} 个探索目标，分布在 ${grouped.size} 个NPC。`}
        />
        <meta name="keywords" content="任务探索,探索任务,地牢探索" />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 20,
        }}
      >
        【任务探索表】探索目标汇总
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 20,
        }}
      >
        共 {data.length} 个探索目标，分布在 {grouped.size} 个NPC
      </div>
      <Disclaimer />
      {[...grouped.entries()].map(([npcName, targets]) => {
        const sorted = [...targets].sort(
          (a, b) => a.quest_number - b.quest_number
        );
        return (
          <div key={npcName} style={{ marginBottom: 24 }}>
            <div
              style={{
                fontSize: 22,
                fontWeight: 'bold',
                color: dark ? '#FFC107' : '#F57F17',
                padding: '5px 0',
                borderBottom: dark ? '2px solid #FFC107' : '2px solid #F57F17',
                marginBottom: 12,
              }}
            >
              {npcName} ({targets.length})
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 8,
              }}
            >
              {sorted.map((t, i) => {
                const mk = modKey(t.module_name);
                const mod = modules.get(mk);
                const sx = mod?.size_x ?? 1;
                const sy = mod?.size_y ?? 1;
                const groupLabel = mod?.group_display || '';
                return (
                  <div
                    key={i}
                    style={{
                      minWidth: 0,
                      gridColumn: sx >= 2 ? `span ${sx}` : undefined,
                      gridRow: sy >= 2 ? `span ${sy}` : undefined,
                      background: tokens.surface,
                      border: `1px solid ${tokens.border}`,
                      borderRadius: 5,
                      padding: 8,
                    }}
                  >
                    <h3
                      style={{
                        margin: '0 0 2px 0',
                        fontSize: 22,
                        color: tokens.accent,
                        textAlign: 'center',
                        width: '100%',
                        lineHeight: 1.3,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {groupLabel && (
                        <span
                          style={{
                            color: dark ? '#FFC107' : '#F57F17',
                            fontSize: 13,
                            fontWeight: 'normal',
                          }}
                        >
                          [{groupLabel}]{' '}
                        </span>
                      )}
                      {t.name || mk}
                    </h3>
                    <div
                      style={{
                        fontSize: 13,
                        color: tokens.muted,
                        marginBottom: 5,
                        textAlign: 'center',
                      }}
                    >
                      {npcName} - 任务: {t.quest_title || `#${t.quest_number}`}
                    </div>
                    <div
                      style={{
                        position: 'relative',
                        width: '100%',
                        paddingBottom: `${(sy / sx) * 100}%`,
                        backgroundColor: tokens.bg,
                        border: `1px solid ${tokens.border}`,
                        borderRadius: 4,
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          backgroundImage: `url(/data/img/${mod?.img_name || mod?.sl_base_name || 'RareModule_1x1'}.webp)`,
                          backgroundSize: 'cover',
                          backgroundPosition: 'center',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
