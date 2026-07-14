import { useEffect, useState } from 'react';

export default function OfflineDetector() {
  const [offline, setOffline] = useState(
    typeof navigator !== 'undefined' && !navigator.onLine
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onOffline = () => setOffline(true);
    const onOnline = () => setOffline(false);
    window.addEventListener('offline', onOffline);
    window.addEventListener('online', onOnline);
    return () => {
      window.removeEventListener('offline', onOffline);
      window.removeEventListener('online', onOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 9998,
        padding: '8px 16px',
        background: '#fa8c16',
        color: '#fff',
        fontSize: 13,
        textAlign: 'center',
      }}
    >
      当前离线，已缓存的页面可正常浏览
    </div>
  );
}
