import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
import type { IndexEntry } from '../types/data';
import Disclaimer from '../components/Disclaimer';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';

const CARD_THEME: Record<
  string,
  { border: string; hoverBg: string; icon: string; titleColor: string }
> = {
  items: {
    border: '#4CAF50',
    hoverBg: 'linear-gradient(145deg, #2a4a2a, #3a5a3a)',
    icon: '📦',
    titleColor: '#fff',
  },
  monsters: {
    border: '#FF6600',
    hoverBg: 'linear-gradient(145deg, #4a3a2a, #5a4a3a)',
    icon: '👹',
    titleColor: '#fff',
  },
  props: {
    border: '#9C27B0',
    hoverBg: 'linear-gradient(145deg, #3a2a4a, #4a3a5a)',
    icon: '🏛️',
    titleColor: '#CE93D8',
  },
  lootdrops: {
    border: '#2196F3',
    hoverBg: 'linear-gradient(145deg, #2a3a4a, #3a4a5a)',
    icon: '💎',
    titleColor: '#fff',
  },
  explore: {
    border: '#0097a7',
    hoverBg: 'linear-gradient(145deg, #2a4a4a, #3a5a5a)',
    icon: '🗺️',
    titleColor: '#0097a7',
  },
  quest_items: {
    border: '#E91E63',
    hoverBg: 'linear-gradient(145deg, #4a2a3a, #5a3a4a)',
    icon: '📋',
    titleColor: '#F06292',
  },
  quest_npc: {
    border: '#FFC107',
    hoverBg: 'linear-gradient(145deg, #4a4a2a, #5a5a3a)',
    icon: '🗡️',
    titleColor: '#FFD54F',
  },
  dungeon_modules: {
    border: '#8BC34A',
    hoverBg: 'linear-gradient(145deg, #2a4a3a, #3a5a4a)',
    icon: '🧩',
    titleColor: '#AED581',
  },
};

const DEFAULT_THEME = {
  border: '#555',
  hoverBg: 'linear-gradient(145deg, #3a3a3a, #444)',
  icon: '📄',
  titleColor: '#fff',
};

export default function HomePage() {
  const ssrData = useSSRData<IndexEntry[]>('home');
  const [data, setData] = useState<IndexEntry[]>(ssrData || []);
  const navigate = useNavigate();
  const dataVersion = useDataVersion();
  const { tokens } = useTheme();

  useEffect(() => {
    if (ssrData) return;
    fetch(`/data/json/index.json?v=${dataVersion}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          越来越黑暗光速指南 DarkFlashNav | 道具、怪物、物品、掉落位置查询
        </title>
        <meta
          name="description"
          content="越来越黑暗光速指南 DarkFlashNav——查询游戏内物品、怪物、实体、掉落物的地图位置，支持坐标偏移调试。"
        />
        <meta property="og:title" content="越来越黑暗光速指南 DarkFlashNav" />
        <meta
          property="og:description"
          content="查询游戏内物品、怪物、实体、掉落物的地图位置"
        />
        <meta property="og:type" content="website" />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 32,
          marginBottom: 12,
        }}
      >
        越来越黑暗光速指南 DarkFlashNav
      </h1>
      <Disclaimer />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 14,
        }}
      >
        {data
          .filter((e) => !('_comment' in e))
          .map((entry) => {
            const t = CARD_THEME[entry.page] ?? DEFAULT_THEME;
            return (
              <div
                key={entry.page}
                onClick={() => navigate(`/${entry.page}/`)}
                style={{
                  background: `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`,
                  border: `2px solid ${t.border}`,
                  borderRadius: 16,
                  padding: '18px 16px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  boxShadow: `0 4px 6px ${tokens.darkShadow}`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = t.hoverBg;
                  e.currentTarget.style.transform =
                    'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = `0 12px 24px ${tokens.deepShadow}`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`;
                  e.currentTarget.style.transform = 'none';
                  e.currentTarget.style.boxShadow = `0 4px 6px ${tokens.darkShadow}`;
                }}
              >
                <div
                  style={{
                    fontSize: 50,
                    marginBottom: 4,
                    filter: `drop-shadow(0 0 8px ${t.border})`,
                  }}
                >
                  {t.icon}
                </div>
                <div
                  style={{
                    color: tokens.text,
                    fontSize: 20,
                    fontWeight: 'bold',
                    marginBottom: 2,
                  }}
                >
                  【{entry.label}】
                </div>
                <div style={{ color: t.titleColor, fontSize: 13 }}>
                  {entry.page === 'quest_items' || entry.page === 'quest_npc'
                    ? `任务${entry.count}个`
                    : `${entry.label}${entry.count}个`}
                </div>
                <div
                  style={{ color: tokens.muted, fontSize: 12, marginTop: 2 }}
                >
                  {entry.page === 'items' && '查看物品位置'}
                  {entry.page === 'monsters' && '查看怪物位置'}
                  {entry.page === 'props' && '查看实体位置'}
                  {entry.page === 'lootdrops' && '查看物品掉落怪物'}
                  {entry.page === 'explore' && '地图模块预览（暂停维护）'}
                  {entry.page === 'quest_items' &&
                    '按地图分组查看任务物品（暂停维护）'}
                  {entry.page === 'quest_npc' && '查看NPC任务详情'}
                  {entry.page === 'dungeon_modules' && '按地图分组查看所有模块'}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}
