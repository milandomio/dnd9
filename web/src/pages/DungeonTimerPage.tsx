import { useCallback, useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { InputNumber, Switch } from 'antd';
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
  const [alertEnabled, setAlertEnabled] = useState(false);
  const [alertSeconds, setAlertSeconds] = useState(30);
  const audioContextRef = useRef<AudioContext | null>(null);
  const lastAlertKeyRef = useRef('');
  const [networkOffsetMs, setNetworkOffsetMs] = useState<number | null>(null);
  const [networkStatus, setNetworkStatus] = useState<'idle' | 'ok' | 'error'>(
    'idle'
  );

  const ensureAudioContext = useCallback(() => {
    const Ctor =
      window.AudioContext ??
      (window as Window & { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctor) return null;
    let ctx = audioContextRef.current;
    if (!ctx) {
      ctx = new Ctor();
      audioContextRef.current = ctx;
    }
    if (ctx.state === 'suspended') void ctx.resume();
    return ctx;
  }, []);

  const playAlert = useCallback(() => {
    const ctx = ensureAudioContext();
    if (!ctx) return;
    // Ten short pulses over five seconds, quiet enough not to startle.
    const start = ctx.currentTime;
    const gain = ctx.createGain();
    gain.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.type = 'square';
    osc.frequency.value = 880;
    osc.connect(gain);
    for (let i = 0; i < 10; i++) {
      const t = start + i * 0.5;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.linearRampToValueAtTime(0.08, t + 0.02);
      gain.gain.setValueAtTime(0.08, t + 0.22);
      gain.gain.linearRampToValueAtTime(0.0001, t + 0.25);
    }
    osc.start(start);
    osc.stop(start + 5.1);
  }, [ensureAudioContext]);

  useEffect(
    () => () => {
      void audioContextRef.current?.close();
      audioContextRef.current = null;
    },
    []
  );

  useEffect(() => {
    if (now === null || !alertEnabled) return;
    // The three open cells always share the same remaining time, so one
    // trigger per rotation window covers every mode.
    const openRemaining = Math.min(
      ...MAPS.map((map) => calculateCountdowns(map.startTime, now).solo)
    );
    // 0 means the window just rolled over; the next window will trigger at
    // its own threshold instead.
    if (openRemaining <= 0 || openRemaining > alertSeconds) return;
    const startOfDay = new Date(now * 1000).setUTCHours(0, 0, 0, 0) / 1000;
    const dayIndex = Math.floor((now - startOfDay) / CYCLE);
    const windowIndex = Math.floor(((now - startOfDay - 1) % CYCLE) / 180);
    const key = `${dayIndex}:${windowIndex}`;
    if (lastAlertKeyRef.current === key) return;
    lastAlertKeyRef.current = key;
    playAlert();
  }, [now, alertEnabled, alertSeconds, playAlert]);

  const handleAlertToggle = (enabled: boolean) => {
    setAlertEnabled(enabled);
    // Creating/resuming here keeps the later automatic alert inside the
    // browser's user-gesture policy.
    if (enabled) ensureAudioContext();
  };

  useEffect(() => {
    const tick = () => setNow(Math.floor(Date.now() / 1000));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const syncNetworkTime = useCallback(async () => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    try {
      const t0 = Date.now();
      // Same-origin request: the HTTP Date header is readable (unlike a
      // cross-origin NTP host, which a browser cannot query over UDP).
      // Unique probe URL: avoids a service worker/precache hit that would
      // hand back a stale Date header.
      const response = await fetch(
        `${window.location.origin}/__timer_clock_probe?t=${t0}`,
        {
          method: 'HEAD',
          cache: 'no-store',
          signal: controller.signal,
        }
      );
      const t1 = Date.now();
      const dateHeader = response.headers.get('date');
      if (!dateHeader) throw new Error('missing Date header');
      const serverMs = Date.parse(dateHeader);
      if (Number.isNaN(serverMs)) throw new Error('invalid Date header');
      // HTTP Date has one-second resolution, so +500 ms removes the average
      // truncation bias; this is a clock comparison, not NTP precision.
      setNetworkOffsetMs(serverMs + 500 - (t0 + t1) / 2);
      setNetworkStatus('ok');
    } catch {
      setNetworkStatus('error');
    } finally {
      window.clearTimeout(timeout);
    }
  }, []);

  useEffect(() => {
    void syncNetworkTime();
    const timer = window.setInterval(() => void syncNetworkTime(), 300000);
    return () => window.clearInterval(timer);
  }, [syncNetworkTime]);

  const openColor = dark ? '#7bd88f' : '#2e7d32';
  const openBackground = dark
    ? 'rgba(123, 216, 143, 0.12)'
    : 'rgba(46, 125, 50, 0.12)';
  const alertColor = dark ? '#64b5f6' : '#1565c0';
  const alertBackground = dark
    ? 'rgba(100, 181, 246, 0.16)'
    : 'rgba(21, 101, 192, 0.12)';
  const driftSeconds =
    networkOffsetMs === null ? 0 : Math.round(Math.abs(networkOffsetMs) / 1000);
  const driftTooLarge =
    networkStatus === 'ok' &&
    networkOffsetMs !== null &&
    Math.abs(networkOffsetMs) > 3000;
  const driftColor = dark ? '#ff6b6b' : '#c62828';
  const networkSeconds =
    now === null || networkOffsetMs === null
      ? null
      : Math.floor(now + networkOffsetMs / 1000);
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

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 12,
          background: tokens.surface,
          borderRadius: 8,
          padding: '10px 16px',
          marginBottom: 16,
        }}
      >
        <span style={{ color: tokens.text, fontWeight: 'bold', fontSize: 14 }}>
          {ut('ui.timer.alert_toggle')}
        </span>
        <Switch
          checked={alertEnabled}
          onChange={handleAlertToggle}
          aria-label={ut('ui.timer.alert_toggle')}
        />
        <InputNumber
          min={5}
          max={180}
          value={alertSeconds}
          disabled={!alertEnabled}
          onChange={(value) => {
            if (typeof value === 'number') setAlertSeconds(value);
          }}
          addonAfter={ut('ui.timer.alert_seconds')}
          style={{ width: 120 }}
        />
        <span style={{ color: tokens.muted, fontSize: 12, flex: '1 1 240px' }}>
          {ut('ui.timer.alert_hint')}
        </span>
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
              gridTemplateColumns: 'minmax(200px, 1.9fr) repeat(3, 1fr)',
              background: tokens.card,
              borderBottom: `1px solid ${tokens.border}`,
              fontWeight: 'bold',
              color: tokens.text,
              fontSize: 14,
            }}
          >
            <div style={{ padding: '10px 14px', lineHeight: 1.6 }}>
              <div>
                {ut('ui.timer.local_time')}:{' '}
                <span style={{ color: tokens.accent }}>
                  {now === null ? '--:--:--' : formatLocalClock(now)}
                </span>
              </div>
              <div>
                {ut('ui.timer.network_time')}:{' '}
                <span
                  style={{
                    color: driftTooLarge
                      ? driftColor
                      : networkStatus === 'ok'
                        ? tokens.text
                        : tokens.muted,
                  }}
                >
                  {networkSeconds === null
                    ? '--:--:--'
                    : formatLocalClock(networkSeconds)}
                </span>
              </div>
              {driftTooLarge && (
                <div style={{ color: driftColor, fontSize: 11 }}>
                  {ut('ui.timer.time_drift').replace(
                    '{seconds}',
                    String(driftSeconds)
                  )}
                </div>
              )}
              {networkStatus === 'error' && (
                <div style={{ color: tokens.muted, fontSize: 11 }}>
                  {ut('ui.timer.network_time_unavailable')}
                </div>
              )}
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
                  gridTemplateColumns: 'minmax(200px, 1.9fr) repeat(3, 1fr)',
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
                  const inAlertWindow =
                    alertEnabled && open && seconds <= alertSeconds;
                  const highlightColor = inAlertWindow ? alertColor : openColor;
                  const highlightBackground = inAlertWindow
                    ? alertBackground
                    : openBackground;
                  return (
                    <div
                      key={mode}
                      style={{
                        padding: '10px 6px',
                        textAlign: 'center',
                        background: open ? highlightBackground : 'transparent',
                      }}
                    >
                      <div
                        style={{
                          fontSize: 22,
                          fontWeight: 700,
                          fontVariantNumeric: 'tabular-nums',
                          color: open ? highlightColor : tokens.text,
                        }}
                      >
                        {seconds === undefined ? '--:--' : formatTime(seconds)}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: open ? highlightColor : tokens.muted,
                          minHeight: 14,
                        }}
                      >
                        {inAlertWindow
                          ? ut('ui.timer.final_window')
                          : open
                            ? ut('ui.timer.open')
                            : ''}
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
        <p style={{ margin: 0 }}>{ut('ui.timer.network_time_note')}</p>
      </div>
    </div>
  );
}
