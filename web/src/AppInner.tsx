/**
 * AppInner — shared route tree with synchronous imports.
 * Used by SSR (ssr.tsx) for server-side rendering.
 * Client entry (App.tsx) uses React.lazy for code splitting instead.
 */
import { Routes, Route } from 'react-router-dom';
import { useTheme } from './hooks/useTheme';
import HomePage from './pages/HomePage';
import ListPage from './pages/ListPage';
import DetailPage from './pages/DetailPage';
import LootdropDetailPage from './pages/LootdropDetailPage';
import ExplorePage from './pages/ExplorePage';
import QuestItemsPage from './pages/QuestItemsPage';
import QuestItemGroupPage from './pages/QuestItemGroupPage';
import QuestNPCPage from './pages/QuestNPCPage';
import QuestNPCDetailPage from './pages/QuestNPCDetailPage';
import DungeonModulesPage from './pages/DungeonModulesPage';
import DungeonModuleGroupPage from './pages/DungeonModuleGroupPage';
import DungeonModuleDetailPage from './pages/DungeonModuleDetailPage';
import NavBar from './components/NavBar';
import Footer from './components/Footer';
import { useRefreshNotice } from './hooks/useDataVersion';

/** Shared page content (routes only, no router wrapper). */
export function AppInner() {
  const { tokens } = useTheme();
  const { needsRefresh, refreshNow } = useRefreshNotice();
  return (
    <div
      style={{
        minHeight: '100vh',
        padding: '16px',
        background: tokens.bg,
        boxSizing: 'border-box',
      }}
    >
      {needsRefresh && (
        <div
          onClick={refreshNow}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            background: '#1677ff',
            color: '#fff',
            textAlign: 'center',
            padding: '8px 16px',
            zIndex: 9999,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          数据已更新，点击刷新页面
        </div>
      )}
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/quest_items" element={<QuestItemsPage />} />
        <Route path="/quest_items/:group" element={<QuestItemGroupPage />} />
        <Route path="/quest_npc" element={<QuestNPCPage />} />
        <Route path="/quest_npc/:npc_name" element={<QuestNPCDetailPage />} />
        <Route path="/dungeon_modules" element={<DungeonModulesPage />} />
        <Route
          path="/dungeon_modules/:group"
          element={<DungeonModuleGroupPage />}
        />
        <Route
          path="/dungeon_modules/:group/:name"
          element={<DungeonModuleDetailPage />}
        />
        <Route path="/lootdrops/:name" element={<LootdropDetailPage />} />
        <Route path="/:page" element={<ListPage />} />
        <Route path="/:page/:name" element={<DetailPage />} />
      </Routes>
      <Footer />
    </div>
  );
}
