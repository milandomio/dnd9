import { HashRouter, Routes, Route } from "react-router-dom";
import { ConfigProvider, Layout, Typography, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import HomePage from "./pages/HomePage";
import ListPage from "./pages/ListPage";
import DetailPage from "./pages/DetailPage";

const { Header, Content } = Layout;

function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: { colorPrimary: "#1677ff" },
      }}
    >
      <HashRouter>
        <Layout style={{ minHeight: "100vh" }}>
          <Header>
            <Typography.Title
              level={3}
              style={{ color: "#fff", margin: 0, lineHeight: "64px", cursor: "pointer" }}
              onClick={() => window.location.hash = "#/"}
            >
              DarkFindV5
            </Typography.Title>
          </Header>
          <Content style={{ padding: "24px" }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/:page" element={<ListPage />} />
              <Route path="/:page/:name" element={<DetailPage />} />
            </Routes>
          </Content>
        </Layout>
      </HashRouter>
    </ConfigProvider>
  );
}

export default App;
