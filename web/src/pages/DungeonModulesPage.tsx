import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Spin, Card, Row, Col } from 'antd';
import { useTheme } from '../hooks/useTheme';
import { useDungeonModules } from '../hooks/useDungeonModules';

interface GroupSummary {
  group: string;
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
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const { tokens } = useTheme();
  const { modules } = useDungeonModules();

  useEffect(() => {
    if (modules.size === 0) return;
    const map = new Map<string, { count: number; display: string }>();
    for (const m of new Set(modules.values())) {
      const g = m.group || '';
      if (!map.has(g)) {
        map.set(g, { count: 0, display: m.group_display || g || '未分组' });
      }
      map.get(g)!.count++;
    }
    const sorted = [...map.entries()]
      .sort(([a], [b]) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b))
      .map(([group, info]) => ({
        group,
        group_display: info.display,
        module_count: info.count,
      }));
    setGroups(sorted);
    setLoading(false);
  }, [modules]);

  if (loading)
    return (
      <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
    );

  const totalMods = groups.reduce((s, g) => s + g.module_count, 0);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>地图模块表 | 越来越黑暗闪电指南 DarkFlashNav</title>
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
        【地图模块表】地图模块汇总
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 24,
        }}
      >
        共 {groups.length} 个地图分组 | {totalMods} 个模块
      </div>
      <Row gutter={[16, 16]} justify="center">
        {groups.map((g) => {
          const theme = GROUP_THEMES[g.group] || { border: '#888', icon: '📦' };
          return (
            <Col key={g.group} xs={24} sm={12} md={8} lg={6}>
              <Link
                to={`/dungeon_modules/${g.group}`}
                style={{ textDecoration: 'none' }}
              >
                <Card
                  hoverable
                  style={{
                    background: `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`,
                    border: `2px solid ${theme.border}`,
                    borderRadius: 12,
                    textAlign: 'center',
                  }}
                  styles={{ body: { padding: '20px 16px' } }}
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
                    {g.group_display}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: tokens.muted,
                      lineHeight: 1.5,
                    }}
                  >
                    {g.module_count} 个模块
                  </div>
                </Card>
              </Link>
            </Col>
          );
        })}
      </Row>
    </div>
  );
}
