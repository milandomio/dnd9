import { ConfigProvider, Layout, Typography, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import HomePage from "./pages/HomePage";

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
      <Layout style={{ minHeight: "100vh" }}>
        <Header>
          <Typography.Title level={3} style={{ color: "#fff", margin: 0, lineHeight: "64px" }}>
            DarkFindV5
          </Typography.Title>
        </Header>
        <Content style={{ padding: "24px" }}>
          <HomePage />
        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
