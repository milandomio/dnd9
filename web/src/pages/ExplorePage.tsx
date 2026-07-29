import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useSSRData } from '../context/SSRDataContext';
import Disclaimer from '../components/Disclaimer';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import { useDungeonModules } from '../hooks/useDungeonModules';
import { useLocale } from '../i18n/useLocale';
import { dataUrl } from '../utils/dataUrl';
import { formatGroupLabel } from '../utils/formatGroupLabel';

interface ExploreTarget {
  name: string;
  module_name: string;
  module_translation_key: string;
  quest_title: string;
  quest_translation_key: string;
  npc_name: string;
  npc_name_display: string;
  npc_translation_key: string;
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
  const { t, ut } = useLocale();

  useEffect(() => {
    if (ssrData) return;
    if (!dataVersion) return;
    fetch(dataUrl(dataVersion, '/data/json/explore.json'))
      .then<ExploreTarget[]>((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, [ssrData, dataVersion]);

  const grouped = new Map<string, ExploreTarget[]>();
  for (const target of data) {
    const key = target.npc_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(target);
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ut('ui.explore.title')} | {ut('ui.brand.name')}
        </title>
        <meta
          name="description"
          content={ut('ui.explore.stat')
            .replace('{count}', String(data.length))
            .replace('{npcCount}', String(grouped.size))}
        />
        <meta name="keywords" content={ut('ui.seo.keywords')} />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 20,
        }}
      >
        {ut('ui.explore.title')}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 20,
        }}
      >
        {ut('ui.explore.stat')
          .replace('{count}', String(data.length))
          .replace('{npcCount}', String(grouped.size))}
      </div>
      <Disclaimer />
      {[...grouped.entries()].map(([npcName, targets]) => {
        const sorted = [...targets].sort(
          (a, b) => a.quest_number - b.quest_number
        );
        const npcDisplayName = t(
          targets[0].npc_translation_key,
          targets[0].npc_name_display || npcName
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
              {npcDisplayName} ({targets.length})
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 8,
              }}
            >
              {sorted.map((target, i) => {
                const mk = modKey(target.module_name);
                const mod = modules.get(mk);
                const sx = mod?.size_x ?? 1;
                const sy = mod?.size_y ?? 1;
                const groupLabel = mod ? formatGroupLabel(mod, t, ut) : '';
                const moduleDisplayName = t(
                  mod?.translation_key || target.module_translation_key,
                  target.name || mod?.translation || mk
                );
                const questDisplayName = t(
                  target.quest_translation_key,
                  target.quest_title || `#${target.quest_number}`
                );
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
                      {moduleDisplayName}
                    </h3>
                    <div
                      style={{
                        fontSize: 13,
                        color: tokens.muted,
                        marginBottom: 5,
                        textAlign: 'center',
                      }}
                    >
                      {npcDisplayName} - {ut('ui.explore.quest')}:{' '}
                      {questDisplayName}
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
