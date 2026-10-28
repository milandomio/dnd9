import { useEffect, useRef, useState } from 'react';
import { useLocale } from '../i18n/useLocale';

type Release = { version: string };
type BannerState = null | 'offline';

function waitForWorkerState(
  worker: ServiceWorker,
  target: 'installed' | 'activated'
) {
  return new Promise<void>((resolve, reject) => {
    let timeout: number | undefined;
    let settled = false;
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      if (timeout !== undefined) window.clearTimeout(timeout);
      worker.removeEventListener('statechange', onStateChange);
      if (error) reject(error);
      else resolve();
    };
    const onStateChange = () => {
      if (worker.state === target) finish();
      else if (worker.state === 'redundant')
        finish(new Error('service worker became redundant before ' + target));
    };
    worker.addEventListener('statechange', onStateChange);
    onStateChange();
    if (!settled) {
      timeout = window.setTimeout(
        () => finish(new Error('service worker timed out before ' + target)),
        15000
      );
    }
  });
}

async function activateWaitingWorker() {
  const registration = await navigator.serviceWorker.getRegistration();
  if (!registration || !navigator.serviceWorker.controller)
    throw new Error('service worker is not ready');

  await registration.update();
  if (!registration.waiting && registration.installing)
    await waitForWorkerState(registration.installing, 'installed');

  const waiting = registration.waiting;
  if (!waiting) throw new Error('new service worker is not waiting');
  if (waiting.state !== 'activated')
    waiting.postMessage({ type: 'SKIP_WAITING' });
  await waitForWorkerState(waiting, 'activated');
}

async function prepareRelease(release: Release) {
  const probeUrl = new URL(window.location.href);
  probeUrl.searchParams.set('_df5_release_check', release.version);
  const response = await fetch(probeUrl, { cache: 'no-store' });
  if (
    !response.ok ||
    !response.headers.get('content-type')?.includes('text/html')
  )
    throw new Error('release HTML is unavailable');
  const html = await response.text();
  const document = new DOMParser().parseFromString(html, 'text/html');
  const pageVersion = document
    .querySelector('meta[name="df5-version"]')
    ?.getAttribute('content');
  if (pageVersion !== release.version)
    throw new Error('release HTML version mismatch');

  const resources = new Set<string>();
  document
    .querySelectorAll('script[src], link[rel="stylesheet"]')
    .forEach((node) => {
      const source = node.getAttribute('src') ?? node.getAttribute('href');
      if (source) resources.add(new URL(source, window.location.href).href);
    });
  document.querySelectorAll('link[rel="preload"][href]').forEach((node) => {
    const source = node.getAttribute('href') ?? '';
    if (
      source.startsWith(`/data/r-${release.version}/json/`) ||
      source.startsWith(`/data/r-${release.version}/img/`)
    )
      resources.add(new URL(source, window.location.href).href);
  });
  const checked = await Promise.all(
    [...resources].map((url) => fetch(url, { cache: 'no-store' }))
  );
  if (checked.some((resource) => !resource.ok))
    throw new Error('a release resource is unavailable');

  await activateWaitingWorker();
  if ('caches' in window) {
    const cache = await caches.open(`df5-html-${release.version}`);
    const headers = new Headers(response.headers);
    headers.delete('content-encoding');
    headers.delete('content-length');
    headers.delete('transfer-encoding');
    await cache.put(
      new Request(window.location.href),
      new Response(html, { headers, status: 200 })
    );
  }
  sessionStorage.setItem('df5_applied_version', release.version);
  window.location.reload();
}

export default function SWUpdateBanner() {
  const { ut } = useLocale();
  const [state, setState] = useState<BannerState>(null);
  const updating = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator))
      return;
    const onUpdate = (event: Event) => {
      const release = (event as CustomEvent<Release>).detail;
      if (!release?.version || updating.current) return;
      updating.current = true;
      void prepareRelease(release).catch(() => {
        updating.current = false;
      });
    };
    window.addEventListener('df5:update-available', onUpdate);
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        if (!navigator.serviceWorker.controller) {
          registration.addEventListener('updatefound', () => {
            const worker = registration.installing;
            worker?.addEventListener('statechange', () => {
              if (
                worker.state === 'installed' &&
                !navigator.serviceWorker.controller
              ) {
                setState('offline');
                window.setTimeout(() => setState(null), 5000);
              }
            });
          });
        }
      })
      .catch(() => {});
    return () => window.removeEventListener('df5:update-available', onUpdate);
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
        background: '#52c41a',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        fontSize: 14,
      }}
    >
      {ut('ui.pwa.offline_ready')}
    </div>
  );
}
