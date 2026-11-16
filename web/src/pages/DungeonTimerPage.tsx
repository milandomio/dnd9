import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';

/** 9-minute cycle; the three modes are three 180 s phases on it. */
const CYCLE = 540;
const STEP = 180;
/** Below this many seconds the countdown turns green = that map is open. */
const GREEN_BELOW = 180;

const MODES = ['solo', 'duo', 'trio'] as const;
type Mode = (typeof MODES)[number];

interface MapDefinition {
  key: string;
  icon: string;
  startTime: number;
  color: string;
}

// Same startTime values as the upstream dad-map-timer MapGrid.vue.
const MAPS: MapDefinition[] = [
  { key: 'castle', icon: '🏰', startTime: 360, color: '#CE93D8' },
  { key: 'goblin', icon: '👺', startTime: 0, color: '#AED581' },
  { key: 'frost', icon: '❄️', startTime: 180, color: '#81D4FA' },
];

type Countdowns = Record<Mode, number>;

/**
 * Mirror of Map.vue: elapsed seconds inside the 540 s cycle, then one
 * 180 s offset per mode. Date.now() is read every tick so waking the
 * machine from sleep cannot desync the clock the way the original does.
 */
function calculateCountdowns(
  startTime: number,
  nowSeconds: number
): Countdowns {
  const startOfDay = new Date(nowSeconds * 1000).setUTCHours(0, 0, 0, 0) / 1000;
  const elapsed =
    (((nowSeconds + startTime - startOfDay - 1) % CYCLE) + CYCLE) % CYCLE;
  return {
    solo: (CYCLE - elapsed) % CYCLE,
    duo: (CYCLE - elapsed + STEP) % CYCLE,
    trio: (CYCLE - elapsed + STEP * 2) % CYCLE,
  };
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

function formatLocalClock(seconds: number): string {
  const date = new Date(seconds * 1000);
  return [date.getHours(), date.getMinutes(), date.getSeconds()]
    .map((value) => String(value).padStart(2, '0'))
    .join(':');
}

export default function DungeonTimerPage() {
  const { dark, tokens } = useTheme();
  const { ut } = useLocale();
  // null on the server and on the first client render: keeps hydration in sync
  // and avoids baking a build-time clock into the static HTML.
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    const tick = () => setNow(Math.floor(Date.now() / 1000));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const openColor = dark ? '#7bd88f' : '#2e7d32';
  const openBackground = dark
    ? 'rgba(123, 216, 143, 0.12)'
    : 'rgba(46, 125, 50, 0.12)';
  const description = ut('ui.timer.description');

  return (
    <div style={{ maxWidth: 'var(--shell-max)' as const, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${ut('ui.timer.title')} | ${ut('ui.brand.name')}`}
        </title>
        <meta name="description" content={description} />
        <meta name="keywords" content={ut('ui.seo.keywords')} />
      </Helmet>

      <h1
        style={{
          textAlign: 'center',
          margin: '8px 0 14px',
          fontSize: 26,
          color: tokens.text,
        }}
      >
        {ut('ui.timer.title')}
      </h1>

      <div
        style={{
          background: tokens.surface,
          borderLeft: `4px solid ${tokens.accent}`,
          borderRadius: 8,
          padding: '12px 16px',
          marginBottom: 16,
        }}
      >
        <div style={{ color: tokens.text, fontWeight: 'bold', fontSize: 15 }}>
          {ut('ui.timer.notice')}
        </div>
        <div style={{ color: tokens.muted, fontSize: 12, marginTop: 4 }}>
          {ut('ui.timer.notice_caveat')}
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <div
          style={{
            minWidth: 520,
            border: `1px solid ${tokens.border}`,
            borderRadius: 12,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(140px, 1.4fr) repeat(3, 1fr)',
              background: tokens.card,
              borderBottom: `1px solid ${tokens.border}`,
              fontWeight: 'bold',
              color: tokens.text,
              fontSize: 14,
            }}
          >
            <div style={{ padding: '10px 14px' }}>
              {ut('ui.timer.local_time')}:{' '}
              <span style={{ color: tokens.accent }}>
                {now === null ? '--:--:--' : formatLocalClock(now)}
              </span>
            </div>
            {MODES.map((mode) => (
              <div
                key={mode}
                style={{ padding: '10px 6px', textAlign: 'center' }}
              >
                {ut(`ui.timer.mode.${mode}`)}
              </div>
            ))}
          </div>

          {MAPS.map((map) => {
            const countdowns =
              now === null ? null : calculateCountdowns(map.startTime, now);
            return (
              <div
                key={map.key}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(140px, 1.4fr) repeat(3, 1fr)',
                  borderBottom: `1px solid ${tokens.border}`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 14px',
                    color: tokens.text,
                    fontSize: 16,
                    fontWeight: 'bold',
                  }}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      fontSize: 26,
                      filter: `drop-shadow(0 0 6px ${map.color})`,
                    }}
                  >
                    {map.icon}
                  </span>
                  {ut(`ui.timer.map.${map.key}`)}
                </div>
                {MODES.map((mode) => {
                  const seconds = countdowns?.[mode];
                  const open = seconds !== undefined && seconds < GREEN_BELOW;
                  return (
                    <div
                      key={mode}
                      style={{
                        padding: '10px 6px',
                        textAlign: 'center',
                        background: open ? openBackground : 'transparent',
                      }}
                    >
                      <div
                        style={{
                          fontSize: 22,
                          fontWeight: 700,
                          fontVariantNumeric: 'tabular-nums',
                          color: open ? openColor : tokens.text,
                        }}
                      >
                        {seconds === undefined ? '--:--' : formatTime(seconds)}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: open ? openColor : tokens.muted,
                          minHeight: 14,
                        }}
                      >
                        {open ? ut('ui.timer.open') : ''}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      <div
        style={{
          color: tokens.muted,
          fontSize: 12,
          lineHeight: 1.7,
          marginTop: 12,
        }}
      >
        <p style={{ margin: 0 }}>{ut('ui.timer.legend')}</p>
        <p style={{ margin: 0 }}>{ut('ui.timer.clock_note')}</p>
      </div>
    </div>
  );
}
