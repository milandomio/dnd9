import { useEffect, useState } from 'react';

export default function SWUpdateBanner() {
  const [needRefresh, setNeedRefresh] = useState(false);
  const [offlineReady, setOfflineReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let wb: any = null;

    import('workbox-window')
      .then(({ Workbox }) => {
        wb = new Workbox('/sw.js', { scope: '/' });
        wb.addEventListener('installed', () => {
          setOfflineReady(true);
        });
        wb.addEventListener('waiting', () => {
          setNeedRefresh(true);
        });
        wb.register({ immediate: true });
      })
      .catch(() => {});
  }, []);

  if (!needRefresh && !offlineReady) return null;

  const handleRefresh = () => {
    let reloaded = false;
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (reloaded) return;
        reloaded = true;
        window.location.reload();
      });
    }
    import('workbox-window').then(({ messageSW }) => {
      if (navigator.serviceWorker.controller) {
        messageSW(navigator.serviceWorker.controller, { type: 'SKIP_WAITING' });
      }
    });
  };

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
      {needRefresh ? (
        <>
          <span>新版本可用</span>
          <button
            onClick={handleRefresh}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.5)',
              borderRadius: 4,
              color: '#fff',
              padding: '4px 12px',
              cursor: 'pointer',
            }}
          >
            立即更新
          </button>
        </>
      ) : (
        <span>离线模式已就绪</span>
      )}
    </div>
  );
}
