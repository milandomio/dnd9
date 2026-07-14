import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import type { IndexEntry } from '../types/data';
import Disclaimer from '../components/Disclaimer';
import { useSSRData } from '../context/SSRDataContext';
import { useTheme } from '../hooks/useTheme';

type CardTheme = {
  border: string;
  hoverBg: string;
  hoverBgLight: string;
  icon: string;
  titleColor: string;
  titleColorLight: string;
};

const CARD_THEME: Record<string, CardTheme> = {
  items: {
    border: '#4CAF50',
    hoverBg: 'linear-gradient(145deg, #2a4a2a, #3a5a3a)',
    hoverBgLight: 'linear-gradient(145deg, #e8f5e9, #c8e6c9)',
    icon: '📦',
    titleColor: '#fff',
    titleColorLight: '#2e7d32',
  },
  monsters: {
    border: '#FF6600',
    hoverBg: 'linear-gradient(145deg, #4a3a2a, #5a4a3a)',
    hoverBgLight: 'linear-gradient(145deg, #fff3e0, #ffe0b2)',
    icon: '👹',
    titleColor: '#fff',
    titleColorLight: '#e65100',
  },
  props: {
    border: '#9C27B0',
    hoverBg: 'linear-gradient(145deg, #3a2a4a, #4a3a5a)',
    hoverBgLight: 'linear-gradient(145deg, #f3e5f5, #e1bee7)',
    icon: '🏛️',
    titleColor: '#CE93D8',
    titleColorLight: '#7b1fa2',
  },
  lootdrops: {
    border: '#2196F3',
    hoverBg: 'linear-gradient(145deg, #2a3a4a, #3a4a5a)',
    hoverBgLight: 'linear-gradient(145deg, #e3f2fd, #bbdefb)',
    icon: '💎',
    titleColor: '#fff',
    titleColorLight: '#1565c0',
  },
  explore: {
    border: '#0097a7',
    hoverBg: 'linear-gradient(145deg, #2a4a4a, #3a5a5a)',
    hoverBgLight: 'linear-gradient(145deg, #e0f7fa, #b2ebf2)',
    icon: '🗺️',
    titleColor: '#0097a7',
    titleColorLight: '#00695c',
  },
  quest_items: {
    border: '#E91E63',
    hoverBg: 'linear-gradient(145deg, #4a2a3a, #5a3a4a)',
    hoverBgLight: 'linear-gradient(145deg, #fce4ec, #f8bbd0)',
    icon: '📋',
    titleColor: '#F06292',
    titleColorLight: '#c2185b',
  },
  quest_npc: {
    border: '#FFC107',
    hoverBg: 'linear-gradient(145deg, #4a4a2a, #5a5a3a)',
    hoverBgLight: 'linear-gradient(145deg, #fff8e1, #ffecb3)',
    icon: '🗡️',
    titleColor: '#FFD54F',
    titleColorLight: '#f57f17',
  },
  dungeon_modules: {
    border: '#8BC34A',
    hoverBg: 'linear-gradient(145deg, #2a4a3a, #3a5a4a)',
    hoverBgLight: 'linear-gradient(145deg, #f1f8e9, #dcedc8)',
    icon: '🧩',
    titleColor: '#AED581',
    titleColorLight: '#558b2f',
  },
};

const DEFAULT_THEME: CardTheme = {
  border: '#555',
  hoverBg: 'linear-gradient(145deg, #3a3a3a, #444)',
  hoverBgLight: 'linear-gradient(145deg, #e0e0e0, #d0d0d0)',
  icon: '📄',
  titleColor: '#fff',
  titleColorLight: '#333',
};

export default function HomePage() {
  const ssrData = useSSRData<IndexEntry[]>('home');
  const [data, setData] = useState<IndexEntry[]>(ssrData || []);
  const { tokens, dark } = useTheme();

  useEffect(() => {
    if (ssrData) return;
    fetch('/data/json/index.json')
      .then((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          越来越黑暗闪电指南 DarkFlashNav |
          游戏地图·任务攻略·BOSS掉落·资源点位·寻找宝箱
        </title>
        <meta
          name="description"
          content="越来越黑暗闪电指南 DarkFlashNav——游戏地图、任务攻略、BOSS掉落、资源点位、寻找宝箱，一站式查询工具。"
        />
        <meta
          name="keywords"
          content="越来越黑暗,越来越黑暗玩家指南,越来越黑暗闪电指南,DarkFlashNav,Dark and Darker,darkanddarker,暗黑地牢,地牢探索,DND,游戏攻略,物品查询,怪物位置,掉落查询,地图坐标,装备属性,武器查询,防具查询,饰品查询,任务攻略,NPC位置,宝箱位置,地牢模块"
        />
        <meta
          property="og:title"
          content="越来越黑暗闪电指南 - 游戏地图·任务攻略·BOSS掉落·资源点位·寻找宝箱"
        />
        <meta
          property="og:description"
          content="游戏地图、任务攻略、BOSS掉落、资源点位、寻找宝箱"
        />
        <meta property="og:type" content="website" />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 26,
          marginBottom: 4,
        }}
      >
        越来越黑暗闪电指南
        <div style={{ fontSize: 14, color: tokens.muted, marginTop: 4 }}>
          DarkFlashNav
        </div>
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
              <Link
                key={entry.page}
                to={`/${entry.page}/`}
                style={{
                  textDecoration: 'none',
                  display: 'block',
                  background: `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`,
                  border: `2px solid ${t.border}`,
                  borderRadius: 16,
                  padding: '18px 16px',
                  textAlign: 'center',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  boxShadow: `0 4px 6px ${tokens.darkShadow}`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = dark
                    ? t.hoverBg
                    : t.hoverBgLight;
                  e.currentTarget.style.transform =
                    'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = `0 12px 24px ${tokens.deepShadow}`;
                  const cc = e.currentTarget.children[2] as HTMLElement;
                  if (cc)
                    cc.style.color = dark ? t.titleColor : t.titleColorLight;
                }}
                onMouseLeave={(e) => {
                  const defBg = `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`;
                  e.currentTarget.style.background = defBg;
                  e.currentTarget.style.transform = 'none';
                  e.currentTarget.style.boxShadow = `0 4px 6px ${tokens.darkShadow}`;
                  const cc = e.currentTarget.children[2] as HTMLElement;
                  if (cc)
                    cc.style.color = dark ? t.titleColor : t.titleColorLight;
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
              </Link>
            );
          })}
      </div>
    </div>
  );
}
