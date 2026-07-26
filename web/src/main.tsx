import ReactDOM from 'react-dom/client';
import App from './App';

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');

const isDetailPlaceholder =
  (
    window as typeof window & {
      __SSR_DATA__?: { __detailTemplate?: boolean };
    }
  ).__SSR_DATA__?.__detailTemplate === true;

if (root.hasChildNodes() && !isDetailPlaceholder) {
  ReactDOM.hydrateRoot(root, <App />);
} else {
  ReactDOM.createRoot(root).render(<App />);
}
