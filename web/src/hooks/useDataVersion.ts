import { useEffect } from 'react';

const BUILD_VERSION = import.meta.env.VITE_DATA_VERSION || 'dev';
const BUILD_DATA_DATE = import.meta.env.VITE_DATA_DATE || '';
const BUILD_SEASON_VERSION = Number(import.meta.env.VITE_SEASON_VERSION || 9);
let lastCheckAt = 0;
let checkPromise: Promise<void> | null = null;
let scheduled = false;

async function checkRelease() {
  if (checkPromise) return checkPromise;
  if (Date.now() - lastCheckAt < 60_000) return;
  lastCheckAt = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  checkPromise = fetch('/data/json/meta.json', {
    cache: 'no-store',
    signal: controller.signal,
  })
    .then((response) => {
      if (!response.ok)
        throw new Error(`release manifest request failed: ${response.status}`);
      return response.json() as Promise<{
        version?: string;
        dataDate?: string;
        seasonVersion?: number;
      }>;
    })
    .then((release) => {
      if (release.version && release.version !== BUILD_VERSION) {
        window.dispatchEvent(
          new CustomEvent('df5:update-available', { detail: release })
        );
      }
    })
    .catch(() => {})
    .finally(() => {
      clearTimeout(timeout);
      checkPromise = null;
    });
  return checkPromise;
}

function scheduleReleaseCheck() {
  if (import.meta.env.DEV || scheduled || typeof window === 'undefined') return;
  scheduled = true;
  const run = () => {
    scheduled = false;
    void checkRelease();
  };
  const idle = (
    window as Window & { requestIdleCallback?: (cb: () => void) => number }
  ).requestIdleCallback;
  if (idle) idle(run);
  else window.setTimeout(run, 1000);
}

export function DataVersionLoader() {
  useEffect(() => {
    const schedule = () => scheduleReleaseCheck();
    const onVisibility = () => {
      if (document.visibilityState === 'visible') scheduleReleaseCheck();
    };
    if (document.readyState === 'complete') schedule();
    else window.addEventListener('load', schedule, { once: true });
    window.addEventListener('online', schedule);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('load', schedule);
      window.removeEventListener('online', schedule);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);
  return null;
}

export function useDataVersion(): string {
  return BUILD_VERSION;
}

export function useDataDate(): string {
  return BUILD_DATA_DATE;
}

export function useSeasonVersion(): number {
  return BUILD_SEASON_VERSION;
}
