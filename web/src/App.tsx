import { BrowserRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from './hooks/useTheme';
import { DebugProvider } from './hooks/useDebug';
import SSRDataContext from './context/SSRDataContext';
import { AppInner } from './AppInner';

/** Client entry: wraps AppInner with BrowserRouter for SPA routing. */
export default function App() {
  const { dark } = useTheme();
  return (
    <HelmetProvider>
      <ThemeProvider>
        <ConfigProvider
          locale={zhCN}
          theme={{
            algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
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
