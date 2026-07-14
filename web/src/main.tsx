import ReactDOM from 'react-dom/client';
import App from './App';

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');

if (root.hasChildNodes()) {
  ReactDOM.hydrateRoot(root, <App />);
} else {
  ReactDOM.createRoot(root).render(<App />);
}
