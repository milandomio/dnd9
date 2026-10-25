/**
 * 归档：【任务物品表】列表页（`/:lang/quest_items`）。
 *
 * 迁移日期：2026-10-25
 * 迁移原因：用户要求把【任务物品表】栏目的代码存档、不再使用，并从主页移除入口。
 *           该栏目的分组详情页（`/:lang/quest_items/:group`）由
 *           `LootdropDetailPage mode="quest_group"` 承担，相关逻辑一并
 *           归档在 `web/src/_archived/QuestGroupMode.tsx`。
 *
 * 恢复方式：
 *   1. 移回 `web/src/pages/QuestItemsPage.tsx`；
 *   2. `web/src/AppInner.tsx` 恢复 `import QuestItemsPage` 与
 *      `<Route path="/:lang/quest_items" element={<QuestItemsPage />} />`、
 *      `<Route path="/:lang/quest_items/:group" element={<LootdropDetailPage mode="quest_group" />} />`；
 *   3. 按 `QuestGroupMode.tsx` 头部说明恢复 `LootdropDetailPage` 的 quest 分支；
 *   4. `web/src/components/NavBar.tsx` 恢复 `quest_items` 的面包屑/搜索标签映射；
 *   5. `web/src/pages/HomePage.tsx` 恢复 `CARD_THEME.quest_items` 与
 *      `quest_items` 的副标题、查看链接分支；
 *   6. `web/scripts/ssg.mjs` 恢复 `SINGLE`/`DETAIL_TEMPLATE_PAGES` 中的 `'quest_items'`、
 *      `questGroups` 路由生成、`ssrDataMap` 注入、`routeDataKey` 分支、
 *      `localizedQuestGroupTitle`、`templateDescription` 的 `quest_items` 分支；
 *   7. 后端恢复 `api/src/_archived/quest_items_groups_export.py` 中的
 *      `generate_quest_items_groups()` 与 `collector.py` 中的调用，
 *      以及 `index_export.build_and_save_indexes()` 的 `quest_items_count` 形参
 *      与 `index.json` 的 `{"page": "quest_items"}` 卡片。
 *
 * 注意：DB 的 `quest_items` 表、`db.import_quest_items()` / `get_quest_items()`、
 *       `save_quest_data()` 的 `quest_items.json` 导出仍在活跃使用（任务 NPC 数据链路），
 *       不属于本次归档范围。
 */
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
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';

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
  const { t, ut, lang, dict } = useLocale();

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
  const description = localizedSeoDescription(lang, dict, 'questItems', {
    groups: groups.length || undefined,
    locations: totalPos || undefined,
  });

  return (
    <div style={{ maxWidth: 'var(--shell-max)' as const, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${ut('ui.quest_items.title')} | ${ut('ui.brand.name')}`}
        </title>
        <meta name="description" content={description} />
        <meta name="keywords" content={ut('ui.seo.keywords')} />
        <meta property="og:description" content={description} />
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
