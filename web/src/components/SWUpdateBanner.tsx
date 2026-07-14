import { useCallback, useEffect, useState } from 'react';

type BannerState = null | 'offline' | 'update';

export default function SWUpdateBanner() {
  const [state, setState] = useState<BannerState>(null);

  const handleRefresh = useCallback(() => {
    window.location.reload();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;

    import('workbox-window')
      .then(({ Workbox }) => {
        const wb = new Workbox('/sw.js', { scope: '/' });

        wb.addEventListener('installed', (event) => {
          if (event.isUpdate) {
            setState('update');
          } else {
            setState('offline');
            setTimeout(() => setState(null), 5000);
          }
        });

        wb.register({ immediate: true });
      })
      .catch(() => {});
  }, []);

  if (!state) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        padding: '10px 16px',
        background: state === 'update' ? '#1677ff' : '#52c41a',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        fontSize: 14,
      }}
    >
      {state === 'offline' && '离线模式已就绪'}
      {state === 'update' && (
        <>
          新版本已下载
          <button
            onClick={handleRefresh}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.4)',
              borderRadius: 4,
              color: '#fff',
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            刷新以应用
          </button>
        </>
      )}
    </div>
  );
}
