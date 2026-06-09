import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import { ThemeProvider, useTheme } from "./hooks/useTheme";
import { DebugProvider } from "./hooks/useDebug";
import HomePage from "./pages/HomePage";
import ListPage from "./pages/ListPage";
import DetailPage from "./pages/DetailPage";
import LootdropDetailPage from "./pages/LootdropDetailPage";
import ExplorePage from "./pages/ExplorePage";
import QuestItemsPage from "./pages/QuestItemsPage";
import QuestNPCPage from "./pages/QuestNPCPage";
import NavBar from "./components/NavBar";

function App() {
  return (
    <HelmetProvider>
    <ConfigProvider
      locale={zhCN}
      theme={{ algorithm: theme.darkAlgorithm, token: { colorPrimary: "#1677ff" } }}
    >
      <ThemeProvider>
        <DebugProvider>
          <BrowserRouter>
            <AppInner />
          </BrowserRouter>
        </DebugProvider>
      </ThemeProvider>
    </ConfigProvider>
    </HelmetProvider>
  );
}

function AppInner() {
  const { tokens } = useTheme();
  return (
    <div style={{ minHeight: "100vh", padding: "24px", background: tokens.bg }}>
      <NavBar />
      <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/quest_items" element={<QuestItemsPage />} />
          <Route path="/quest_npc" element={<QuestNPCPage />} />
          <Route path="/:page" element={<ListPage />} />
          <Route path="/lootdrops/:name" element={<LootdropDetailPage />} />
          <Route path="/:page/:name" element={<DetailPage />} />
      </Routes>
    </div>
  );
}

export default App;
