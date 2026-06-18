import { BrowserRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider } from './hooks/useTheme';
import { DebugProvider } from './hooks/useDebug';
import SSRDataContext from './context/SSRDataContext';
import { AppInner } from './AppInner';

/** Client entry — component tree must match SSR (ssr.tsx) exactly. */
export default function App() {
  return (
    <HelmetProvider>
      <ThemeProvider>
        <ConfigProvider
          locale={zhCN}
          theme={{
            algorithm: theme.darkAlgorithm,
            token: { colorPrimary: '#1677ff' },
          }}
        >
          <DebugProvider>
            <SSRDataContext.Provider value={null}>
              <BrowserRouter>
                <AppInner />
              </BrowserRouter>
            </SSRDataContext.Provider>
          </DebugProvider>
        </ConfigProvider>
      </ThemeProvider>
    </HelmetProvider>
  );
}
