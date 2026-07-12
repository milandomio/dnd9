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

const GROUP_LABELS: Record<string, string> = {
  Crypt: '废墟2层地牢',
  FireDeep: '哥布林洞穴2层',
  GoblinCave: '哥布林洞穴1层',
  IceAbyss: '冰图2层',
  IceCavern: '冰图1层',
  Inferno: '废墟3层炼狱',
  Ruins: '废墟1层',
  ShipGraveyard: '水图',
};

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
  'Crypt',
  'FireDeep',
  'GoblinCave',
  'IceAbyss',
  'IceCavern',
  'Inferno',
  'Ruins',
  'ShipGraveyard',
];

export default function DungeonModulesPage() {
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const { tokens } = useTheme();
  const { modules } = useDungeonModules();

  useEffect(() => {
    if (modules.size === 0) return;
    const map = new Map<string, number>();
    for (const m of new Set(modules.values())) {
      const g = m.group || '';
      map.set(g, (map.get(g) || 0) + 1);
    }
    const sorted = [...map.entries()]
      .sort(([a], [b]) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b))
      .map(([group, count]) => ({
        group,
        group_display: GROUP_LABELS[group] || group || '未分组',
        module_count: count,
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
        <title>地图模块表 | 越来越黑暗光速指南 DarkFlashNav</title>
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
                  bodyStyle={{ padding: '20px 16px' }}
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
