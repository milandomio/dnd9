import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';

/** Slow constant speed (CSS px per second) so recordings stay readable. */
const SCROLL_SPEED = 60;

function maxScrollTop() {
  return Math.max(
    0,
    document.documentElement.scrollHeight - window.innerHeight
  );
}

/**
 * Navbar play/pause button that slowly scrolls the page to the bottom.
 * Intended for screen recording: wheel / touch / scroll-key input pauses it.
 */
export default function AutoScrollButton() {
  const { dark, tokens } = useTheme();
  const { ut } = useLocale();
  const { pathname } = useLocation();
  const [running, setRunning] = useState(false);

  // Route change invalidates the recording run.
  useEffect(() => {
    setRunning(false);
  }, [pathname]);

  useEffect(() => {
    if (!running) return;
    let frame = 0;
    let last = performance.now();

    const step = (now: number) => {
      const dt = Math.min(now - last, 50) / 1000;
      last = now;
      const max = maxScrollTop();
      const next = Math.min(window.scrollY + SCROLL_SPEED * dt, max);
      window.scrollTo(0, next);
      if (next >= max - 0.5) {
        setRunning(false);
        return;
      }
      frame = requestAnimationFrame(step);
    };

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [running]);

  // Manual scrolling wins over the auto-scroll.
  useEffect(() => {
    if (!running) return;
    const stop = () => setRunning(false);
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        [
          'ArrowDown',
          'ArrowUp',
          'PageDown',
          'PageUp',
          'Home',
          'End',
          ' ',
        ].includes(e.key)
      ) {
        stop();
      }
    };
    window.addEventListener('wheel', stop, { passive: true });
    window.addEventListener('touchstart', stop, { passive: true });
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('wheel', stop);
      window.removeEventListener('touchstart', stop);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [running]);

  const toggle = () => {
    if (running) {
      setRunning(false);
      return;
    }
    const max = maxScrollTop();
    if (max <= 0) return;
    // Already at the bottom: replay from the top.
    if (window.scrollY >= max - 1) window.scrollTo(0, 0);
    setRunning(true);
  };

  const label = ut(running ? 'ui.autoscroll.pause' : 'ui.autoscroll.play');

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      aria-pressed={running}
      title={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 28,
        height: 24,
        padding: 0,
        color: running ? (dark ? '#2c2c2c' : '#fff') : tokens.accent,
        background: running ? tokens.accent : dark ? '#141414' : '#fff',
        border: `1px solid ${running ? tokens.accent : tokens.border}`,
        borderRadius: 6,
        cursor: 'pointer',
        lineHeight: 1,
        transition: 'all 0.2s',
      }}
    >
      {running ? (
        <PauseCircleOutlined style={{ fontSize: 16 }} />
      ) : (
        <PlayCircleOutlined style={{ fontSize: 16 }} />
      )}
    </button>
  );
}
