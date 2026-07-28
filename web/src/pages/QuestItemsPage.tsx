import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Spin, Card, Row, Col } from 'antd';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import { dataUrl } from '../utils/dataUrl';
import { formatGroupLabel } from '../utils/formatGroupLabel';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';

interface GroupEntry {
  group: string;
  group_key?: string;
  group_floor?: number;
  group_sub_key?: string | null;
  group_display: string;
  entity_count: number;
  position_count: number;
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

export default function QuestItemsPage() {
  const ssrData = useSSRData<GroupEntry[]>('quest_items');
  const [groups, setGroups] = useState<GroupEntry[]>(ssrData || []);
  const [loading, setLoading] = useState(!ssrData);
  const dataVersion = useDataVersion();
  const { tokens } = useTheme();
  const { t, ut, lang } = useLocale();

  useEffect(() => {
    if (ssrData) return;
    if (!dataVersion) return;
    fetch(dataUrl(dataVersion, '/data/json/quest_items_groups.json'))
      .then((r) => r.json())
      .then(setGroups)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [ssrData, dataVersion]);

  if (loading)
    return (
      <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
    );

  const totalPos = groups.reduce((s, g) => s + g.position_count, 0);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>任务物品表 | 越来越黑暗闪电指南 DarkFlashNav</title>
        <meta
          name="description"
          content="任务物品查询——按地图分组查看任务物品分布。"
        />
        <meta name="keywords" content="任务物品,任务攻略,任务查询" />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 10,
        }}
      >
        {ut('ui.quest_items.title')}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 24,
        }}
      >
        {ut('ui.quest_items.stat')
          .replace('{groups}', String(groups.length))
          .replace('{total}', String(totalPos))}
      </div>
      <Row gutter={[16, 16]} justify="center">
        {groups.map((g) => {
          const theme = GROUP_THEMES[g.group] || { border: '#888', icon: '📦' };
          return (
            <Col key={g.group} xs={24} sm={12} md={8} lg={6}>
              <Link
                to={`/${lang}/quest_items/${g.group}`}
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
                    {formatGroupLabel(g, t, ut)}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: tokens.muted,
                      lineHeight: 1.5,
                    }}
                  >
                    {ut('ui.quest_items.entity').replace(
                      '{count}',
                      String(g.entity_count)
                    )}
                    <br />
                    {ut('ui.quest_items.pos').replace(
                      '{count}',
                      String(g.position_count)
                    )}
                  </div>
                </Card>
              </Link>
            </Col>
          );
        })}
      </Row>
      <div
        style={{
          textAlign: 'center',
          marginTop: 32,
          color: tokens.muted,
          fontSize: 14,
        }}
      >
        {ut('ui.quest_items.footer')}
      </div>
    </div>
  );
}
