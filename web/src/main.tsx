import ReactDOM from 'react-dom/client';
import App from './App';
import { isSupportedLang } from './i18n/locale';

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');

const isDetailPlaceholder = root.dataset.detailPlaceholder !== undefined;
const ssrData = (window as any).__SSR_DATA__ as
  | Record<string, unknown>
  | undefined;

function hasRouteSsrData(): boolean {
  if (!ssrData) return false;
  const parts = window.location.pathname.split('/').filter(Boolean);
  if (parts[0] && isSupportedLang(parts[0])) parts.shift();
  if (parts.length === 0) return Boolean(ssrData.home);

  const page = parts[0];
  if (['items', 'monsters', 'props', 'lootdrops'].includes(page) && parts[1]) {
    return Boolean(ssrData[`${page}/${decodeURIComponent(parts[1])}`]);
  }
  if (page === 'quest_items' && parts[1]) {
    return Boolean(ssrData[`quest_items_groups/${parts[1]}`]);
  }
  if (page === 'dungeon_modules' && parts[1] && parts[2]) {
    return Boolean(ssrData[`dungeon_modules_detail/${parts[1]}/${parts[2]}`]);
  }
  return Boolean(ssrData[`list-${page}`] ?? ssrData[page]);
}

if (root.hasChildNodes() && !isDetailPlaceholder && hasRouteSsrData()) {
  ReactDOM.hydrateRoot(root, <App />);
} else {
  ReactDOM.createRoot(root).render(<App />);
}
