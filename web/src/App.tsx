import { HashRouter, Routes, Route } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import { ThemeProvider, useTheme } from "./hooks/useTheme";
import { DebugProvider } from "./hooks/useDebug";
import HomePage from "./pages/HomePage";
import ListPage from "./pages/ListPage";
import DetailPage from "./pages/DetailPage";
import ExplorePage from "./pages/ExplorePage";
import QuestItemsPage from "./pages/QuestItemsPage";
import QuestNPCPage from "./pages/QuestNPCPage";
import NavBar from "./components/NavBar";

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{ algorithm: theme.darkAlgorithm, token: { colorPrimary: "#1677ff" } }}
    >
      <ThemeProvider>
        <DebugProvider>
          <HashRouter>
            <AppInner />
          </HashRouter>
        </DebugProvider>
      </ThemeProvider>
    </ConfigProvider>
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
          <Route path="/:page/:name" element={<DetailPage />} />
      </Routes>
    </div>
  );
}

export default App;
