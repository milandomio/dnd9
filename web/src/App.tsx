import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { ConfigProvider, theme, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from './hooks/useTheme';
import { DebugProvider } from './hooks/useDebug';
import NavBar from './components/NavBar';

// Small / frequently-visited pages — synchronous imports
import HomePage from './pages/HomePage';
import ListPage from './pages/ListPage';
import ExplorePage from './pages/ExplorePage';
import QuestItemsPage from './pages/QuestItemsPage';
import QuestNPCPage from './pages/QuestNPCPage';
import DungeonModulesPage from './pages/DungeonModulesPage';

// Heavy detail pages — lazy-loaded (code splitting)
const DetailPage = lazy(() => import('./pages/DetailPage'));
const LootdropDetailPage = lazy(() => import('./pages/LootdropDetailPage'));
const QuestItemGroupPage = lazy(() => import('./pages/QuestItemGroupPage'));
const QuestNPCDetailPage = lazy(() => import('./pages/QuestNPCDetailPage'));
const DungeonModuleGroupPage = lazy(
  () => import('./pages/DungeonModuleGroupPage')
);
const DungeonModuleDetailPage = lazy(
  () => import('./pages/DungeonModuleDetailPage')
);

function PageLoader() {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '50vh',
      }}
    >
      <Spin size="large" />
    </div>
  );
}

function AppRoutes() {
  const { tokens } = useTheme();
  return (
    <div style={{ minHeight: '100vh', padding: '24px', background: tokens.bg }}>
      <NavBar />
      <Suspense fallback={<PageLoader />}>
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
      </Suspense>
    </div>
  );
}

function AntdConfigProvider({ children }: { children: React.ReactNode }) {
  const { dark } = useTheme();
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: { colorPrimary: '#1677ff' },
      }}
    >
      {children}
    </ConfigProvider>
  );
}

/** Client entry: wraps AppRoutes with BrowserRouter for SPA routing. */
export default function App() {
  return (
    <HelmetProvider>
      <ThemeProvider>
        <AntdConfigProvider>
          <DebugProvider>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </DebugProvider>
        </AntdConfigProvider>
      </ThemeProvider>
    </HelmetProvider>
  );
}
