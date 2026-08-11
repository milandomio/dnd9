/**
 * AppInner — shared route tree with synchronous imports.
 * Used by SSR (ssr.tsx) for server-side rendering.
 * Client entry (App.tsx) uses React.lazy for code splitting instead.
 */
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { useTheme } from './hooks/useTheme';
import { useDungeonModules } from './hooks/useDungeonModules';
import HomePage from './pages/HomePage';
import ListPage from './pages/ListPage';
import DetailPage from './pages/DetailPage';
import LootdropDetailPage from './pages/LootdropDetailPage';
import ExplorePage from './pages/ExplorePage';
import QuestItemsPage from './pages/QuestItemsPage';
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
import { LanguageProvider } from './i18n/LanguageContext';
import { DEFAULT_LANG, isSupportedLang } from './i18n/locale';
import { useAntdLocale } from './i18n/antdLocale';
import type { ReactNode } from 'react';
import { useLocale } from './i18n/useLocale';

function AntdLocaleProvider({ children }: { children: ReactNode }) {
  const locale = useAntdLocale();
  return <ConfigProvider locale={locale}>{children}</ConfigProvider>;
}

/**
 * Paths without a supported lang prefix (e.g. /monsters/X/) would otherwise
 * match /:lang/:page with lang="monsters". Redirect before Routes match.
 */
function AppRoutes() {
  const location = useLocation();
  const segment = location.pathname.split('/').filter(Boolean)[0];
  if (segment && !isSupportedLang(segment)) {
    return (
      <Navigate
        to={`/${DEFAULT_LANG}${location.pathname}${location.search}${location.hash}`}
        replace
      />
    );
  }
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/:lang" element={<HomePage />} />
      <Route path="/:lang/explore" element={<ExplorePage />} />
      <Route path="/:lang/quest_items" element={<QuestItemsPage />} />
      <Route
        path="/:lang/quest_items/:group"
        element={<LootdropDetailPage mode="quest_group" />}
      />
      <Route path="/:lang/quest_npc" element={<QuestNPCPage />} />
      <Route
        path="/:lang/quest_npc/:npc_name"
        element={<QuestNPCDetailPage />}
      />
      <Route path="/:lang/dungeon_modules" element={<DungeonModulesPage />} />
      <Route
        path="/:lang/dungeon_modules/:group"
        element={<DungeonModuleGroupPage />}
      />
      <Route
        path="/:lang/dungeon_modules/:group/:name"
        element={<DungeonModuleDetailPage />}
      />
      <Route path="/:lang/lootdrops/:name" element={<LootdropDetailPage />} />
      <Route path="/:lang/:page" element={<ListPage />} />
      <Route path="/:lang/:page/:name" element={<DetailPage />} />
    </Routes>
  );
}

/** Shared page content (routes only, no router wrapper). */
function LocalizedApp() {
  const { tokens } = useTheme();
  const { localeReady } = useLocale();

  return (
    <AntdLocaleProvider>
      <div
        style={{
          minHeight: '100vh',
          padding: '16px',
          background: tokens.bg,
          boxSizing: 'border-box',
          maxWidth: 1200,
          margin: '0 auto',
        }}
      >
        <SWUpdateBanner />
        <OfflineDetector />
        <InstallPrompt />
        <NavBar />
        <div aria-busy={!localeReady}>
          <AppRoutes />
        </div>
        <Footer />
      </div>
    </AntdLocaleProvider>
  );
}

export function AppInner() {
  useDungeonModules(); // preload data version and module data before locale gate opens
  return (
    <LanguageProvider>
      <LocalizedApp />
    </LanguageProvider>
  );
}
