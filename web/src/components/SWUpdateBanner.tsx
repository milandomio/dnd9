import { useEffect, useState } from 'react';

export default function SWUpdateBanner() {
  const [offlineReady, setOfflineReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;

    import('workbox-window')
      .then(({ Workbox }) => {
        const wb = new Workbox('/sw.js', { scope: '/' });
        wb.addEventListener('installed', () => {
          setOfflineReady(true);
          setTimeout(() => setOfflineReady(false), 5000);
        });
        wb.register({ immediate: true });
      })
      .catch(() => {});
  }, []);

  if (!offlineReady) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        padding: '10px 16px',
        background: '#1677ff',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        fontSize: 14,
      }}
    >
      离线模式已就绪
    </div>
  );
}
