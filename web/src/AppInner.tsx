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
import SWUpdateBanner from './components/SWUpdateBanner';
import OfflineDetector from './components/OfflineDetector';
import InstallPrompt from './components/InstallPrompt';

/** Shared page content (routes only, no router wrapper). */
export function AppInner() {
  const { tokens } = useTheme();
  return (
    <div
      style={{
        minHeight: '100vh',
        padding: '16px',
        background: tokens.bg,
        boxSizing: 'border-box',
      }}
    >
      <SWUpdateBanner />
      <OfflineDetector />
      <InstallPrompt />
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
