import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useDungeonModules } from '../hooks/useDungeonModules';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';
import { formatGroupLabel } from '../utils/formatGroupLabel';

interface GroupSummary {
  group: string;
  group_key?: string;
  group_floor?: number;
  group_sub_key?: string | null;
  group_display: string;
  module_count: number;
}

const GROUP_THEMES: Record<string, { border: string; icon: string }> = {
  Crypt: { border: '#E91E63', icon: '💀' },
  FireDeep: { border: '#FF5722', icon: '🔥' },
  GoblinCave: { border: '#4CAF50', icon: '🍄' },
  IceAbyss: { border: '#00BCD4', icon: '❄️' },
  IceCavern: { border: '#2196F3', icon: '🧊' },
  Inferno: { border: '#F44336', icon: '🌋' },
  Ruins: { border: '#9C27B0', icon: '🏛️' },
  ShipGraveyard: { border: '#607D8B', icon: '⚓' },
};

const GROUP_ORDER = [
  'GoblinCave',
  'FireDeep',
  'IceCavern',
  'IceAbyss',
  'Ruins',
  'Crypt',
  'Inferno',
  'ShipGraveyard',
];

export default function DungeonModulesPage() {
  const ssrGroups = useSSRData<GroupSummary[]>('dungeon_modules');
  const [groups, setGroups] = useState<GroupSummary[]>(ssrGroups ?? []);
  const [loading, setLoading] = useState(!ssrGroups);
  const { tokens } = useTheme();
  const { modules } = useDungeonModules();
  const { t, ut, lang } = useLocale();

  useEffect(() => {
    if (ssrGroups) return;
    if (modules.size === 0) return;
    const map = new Map<
      string,
      {
        count: number;
        group_key?: string;
        group_floor?: number;
        group_sub_key?: string | null;
        group_display: string;
      }
    >();
    for (const m of new Set(modules.values())) {
      const g = m.group || '';
      if (!map.has(g)) {
        map.set(g, {
          count: 0,
          group_key: m.group_key,
          group_floor: m.group_floor,
          group_sub_key: m.group_sub_key,
          group_display: m.group_display || g || '未分组',
        });
      }
      map.get(g)!.count++;
    }
    const sorted = [...map.entries()]
      .sort(([a], [b]) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b))
      .map(([group, info]) => ({
        group,
        group_key: info.group_key,
        group_floor: info.group_floor,
        group_sub_key: info.group_sub_key,
        group_display: info.group_display,
        module_count: info.count,
      }));
    setGroups(sorted);
    setLoading(false);
  }, [modules, ssrGroups]);

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  const totalMods = groups.reduce((s, g) => s + g.module_count, 0);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>{ut('ui.module.title')} | 越来越黑暗闪电指南 DarkFlashNav</title>
        <meta
          name="description"
          content="地图模块查询——按地图分组查看所有模块。"
        />
        <meta name="keywords" content="地牢模块,地图模块,地牢坐标,地图坐标" />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 10,
        }}
      >
        {ut('ui.module.title')}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 24,
        }}
      >
        {ut('ui.module.stat')
          .replace('{groups}', String(groups.length))
          .replace('{total}', String(totalMods))}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 16,
          maxWidth: 900,
          margin: '0 auto',
        }}
      >
        {groups.map((g) => {
          const theme = GROUP_THEMES[g.group] || { border: '#888', icon: '📦' };
          return (
            <Link
              key={g.group}
              to={`/${lang}/dungeon_modules/${g.group}`}
              style={{ textDecoration: 'none' }}
            >
              <div
                style={{
                  background: `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`,
                  border: `2px solid ${theme.border}`,
                  borderRadius: 12,
                  textAlign: 'center',
                  padding: '20px 16px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-3px)';
                  e.currentTarget.style.boxShadow =
                    '0 6px 16px rgba(0,0,0,0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'none';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: 36, marginBottom: 8 }}>
                  {theme.icon}
                </div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 'bold',
                    color: tokens.text,
                    marginBottom: 8,
                  }}
                >
                  {formatGroupLabel(g, t, ut)}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: tokens.muted,
                    lineHeight: 1.5,
                  }}
                >
                  {ut('ui.module.count').replace(
                    '{count}',
                    String(g.module_count)
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
