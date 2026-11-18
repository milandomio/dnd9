import {
  type ChangeEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Helmet } from 'react-helmet-async';
import { AutoComplete, Button, InputNumber, Modal, Select, Switch } from 'antd';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';

/** Base rotation options in seconds; the cycle is three of these windows. */
const ROTATION_OPTIONS = [180, 240, 300] as const;
const DEFAULT_ROTATION = 180;

const MODES = ['solo', 'duo', 'trio'] as const;
/** Alert queue dropdown order: trio first, then duo, then solo. */
const ALERT_MODE_OPTIONS = ['trio', 'duo', 'solo'] as const;
/** Alert thresholds: 15 s then every 30 s up to 165 s (180 s window − 15 s). */
const ALERT_OPTIONS = Array.from({ length: 6 }, (_, index) => 15 + index * 30);
/** Built-in alert sounds plus a user-uploaded audio file. */
const SOUND_PRESETS = [
  'default',
  'alarm-classic',
  'alarm-digital',
  'alarm-siren',
  'alarm-bell',
  'custom',
] as const;
type Mode = (typeof MODES)[number];
type SoundPreset = (typeof SOUND_PRESETS)[number];

interface MapDefinition {
  key: string;
  icon: string;
  /** How many rotation windows this map's phase is offset by. */
  offsetWindows: number;
  color: string;
}

// Display order follows the Solo rotation: Goblin Cave -> Ruins -> Frost.
// Offsets are the same phases as the upstream startTime values (0/180/360).
const MAPS: MapDefinition[] = [
  { key: 'goblin', icon: '👺', offsetWindows: 0, color: '#AED581' },
  { key: 'castle', icon: '🏰', offsetWindows: 2, color: '#CE93D8' },
  { key: 'frost', icon: '❄️', offsetWindows: 1, color: '#81D4FA' },
];

type Countdowns = Record<Mode, number>;

/**
 * Map.vue generalised to a configurable window: the cycle is three windows
 * and each mode is offset by one window. Date.now() is read every tick so
 * waking from sleep cannot desync the clock the way the original does.
 */
function calculateCountdowns(
  offsetWindows: number,
  nowSeconds: number,
  windowSeconds: number
): Countdowns {
  const cycle = windowSeconds * 3;
  const startOfDay = new Date(nowSeconds * 1000).setUTCHours(0, 0, 0, 0) / 1000;
  const elapsed =
    (((nowSeconds - startOfDay - 1 + offsetWindows * windowSeconds) % cycle) +
      cycle) %
    cycle;
  return {
    solo: (cycle - elapsed) % cycle,
    duo: (cycle - elapsed + windowSeconds) % cycle,
    trio: (cycle - elapsed + windowSeconds * 2) % cycle,
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

// Uploaded alert sounds stay in this browser (IndexedDB). The site is static
// and never receives the file; an object URL is created at runtime.
const SOUND_DB = 'darkfind-timer';
const SOUND_STORE = 'alert-sounds';
const SOUND_RECORD_KEY = 'custom';
const SOUND_PRESET_STORAGE_KEY = 'darkfind.timer.soundPreset';

interface StoredSound {
  blob: Blob;
  name: string;
}

function openSoundDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SOUND_DB, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(SOUND_STORE)) {
        db.createObjectStore(SOUND_STORE);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function saveStoredSound(sound: StoredSound): Promise<void> {
  const db = await openSoundDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(SOUND_STORE, 'readwrite');
      tx.objectStore(SOUND_STORE).put(sound, SOUND_RECORD_KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

async function loadStoredSound(): Promise<StoredSound | null> {
  const db = await openSoundDb();
  try {
    return await new Promise<StoredSound | null>((resolve, reject) => {
      const tx = db.transaction(SOUND_STORE, 'readonly');
      const request = tx.objectStore(SOUND_STORE).get(SOUND_RECORD_KEY);
      request.onsuccess = () =>
        resolve((request.result as StoredSound | undefined) ?? null);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export default function DungeonTimerPage() {
  const { dark, tokens } = useTheme();
  const { ut } = useLocale();
  // null on the server and on the first client render: keeps hydration in sync
  // and avoids baking a build-time clock into the static HTML.
  const [now, setNow] = useState<number | null>(null);
  const [popupEnabled, setPopupEnabled] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [soundPreset, setSoundPreset] = useState<SoundPreset>('default');
  const [customAudioUrl, setCustomAudioUrl] = useState<string | null>(null);
  const [customAudioName, setCustomAudioName] = useState('');
  const [backgroundMode, setBackgroundMode] = useState(false);
  const [alertSeconds, setAlertSeconds] = useState(15);
  const [alertSecondsText, setAlertSecondsText] = useState('15');
  const [paused, setPaused] = useState(false);
  const [rotationSeconds, setRotationSeconds] = useState(DEFAULT_ROTATION);
  const [rotationCustom, setRotationCustom] = useState(false);
  const [alertMode, setAlertMode] = useState<Mode>('trio');
  const [alertMapKey, setAlertMapKey] = useState('castle');
  const [popup, setPopup] = useState<{
    mapKey: string;
    mode: Mode;
    seconds: number;
  } | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const keepAliveRef = useRef<{
    osc: OscillatorNode;
    gain: GainNode;
  } | null>(null);
  const lastAlertKeyRef = useRef('');
  const soundFileInputRef = useRef<HTMLInputElement | null>(null);
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

  const playSound = useCallback(
    (preset: SoundPreset, url: string | null) => {
      if (preset === 'custom') {
        if (!url) return;
        const audio = new Audio(url);
        void audio.play().catch(() => {
          // Autoplay refused or clip unavailable: short synthesised ding.
          const ctx = ensureAudioContext();
          if (!ctx) return;
          const gain = ctx.createGain();
          gain.gain.value = 0.06;
          gain.connect(ctx.destination);
          const osc = ctx.createOscillator();
          osc.frequency.value = 880;
          osc.connect(gain);
          osc.start();
          osc.stop(ctx.currentTime + 0.3);
        });
        return;
      }

      const ctx = ensureAudioContext();
      if (!ctx) return;
      const start = ctx.currentTime;
      const beep = (
        freq: number,
        offset: number,
        duration: number,
        type: OscillatorType = 'square',
        peak = 0.08
      ) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        osc.connect(gain);
        gain.connect(ctx.destination);
        const t = start + offset;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.linearRampToValueAtTime(peak, t + 0.015);
        gain.gain.setValueAtTime(peak, t + duration - 0.04);
        gain.gain.linearRampToValueAtTime(0.0001, t + duration);
        osc.start(t);
        osc.stop(t + duration + 0.02);
      };

      // Three-second alarm patterns; no audio files are downloaded.
      if (preset === 'alarm-classic') {
        for (let i = 0; i < 10; i++) {
          beep(i % 2 ? 880 : 1046, i * 0.3, 0.16);
        }
        return;
      }
      if (preset === 'alarm-digital') {
        for (let i = 0; i < 12; i++) {
          beep(1400, i * 0.24, 0.1, 'square', 0.07);
        }
        return;
      }
      if (preset === 'alarm-siren') {
        for (let i = 0; i < 12; i++) {
          beep(i % 2 ? 660 : 990, i * 0.25, 0.2, 'triangle', 0.08);
        }
        return;
      }
      if (preset === 'alarm-bell') {
        for (let i = 0; i < 5; i++) {
          beep(880, i * 0.6, 0.45, 'sine', 0.09);
          beep(1760, i * 0.6, 0.25, 'sine', 0.03);
        }
        return;
      }

      // default: original four short square pulses.
      const gain = ctx.createGain();
      gain.connect(ctx.destination);
      const osc = ctx.createOscillator();
      osc.type = 'square';
      osc.frequency.value = 880;
      osc.connect(gain);
      for (let i = 0; i < 4; i++) {
        const t = start + i * 0.5;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.linearRampToValueAtTime(0.08, t + 0.02);
        gain.gain.setValueAtTime(0.08, t + 0.22);
        gain.gain.linearRampToValueAtTime(0.0001, t + 0.25);
      }
      osc.start(start);
      osc.stop(start + 2.1);
    },
    [ensureAudioContext]
  );

  const playAlert = useCallback(() => {
    playSound(soundPreset, customAudioUrl);
  }, [playSound, soundPreset, customAudioUrl]);

  const handleSoundFile = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      if (customAudioUrl) URL.revokeObjectURL(customAudioUrl);
      const url = URL.createObjectURL(file);
      setCustomAudioUrl(url);
      setCustomAudioName(file.name);
      setSoundPreset('custom');
      setSoundEnabled(true);
      ensureAudioContext();
      void saveStoredSound({ blob: file, name: file.name }).catch(() => {
        // Storage unavailable (private mode/quota): keep session-only.
      });
      playSound('custom', url);
      // Allow re-selecting the same file later.
      event.target.value = '';
    },
    [customAudioUrl, ensureAudioContext, playSound]
  );

  useEffect(
    () => () => {
      if (customAudioUrl) URL.revokeObjectURL(customAudioUrl);
    },
    [customAudioUrl]
  );

  // Restore the stored sound and last selection from this browser.
  const soundHydratedRef = useRef(false);
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const stored = await loadStoredSound();
        if (cancelled) return;
        if (stored) {
          setCustomAudioName(stored.name);
          setCustomAudioUrl(URL.createObjectURL(stored.blob));
        }
        const savedPreset = localStorage.getItem(
          SOUND_PRESET_STORAGE_KEY
        ) as SoundPreset | null;
        if (
          savedPreset &&
          (SOUND_PRESETS as readonly string[]).includes(savedPreset) &&
          (savedPreset !== 'custom' || stored)
        ) {
          setSoundPreset(savedPreset);
        }
      } catch {
        // IndexedDB/localStorage unavailable: keep defaults.
      } finally {
        if (!cancelled) soundHydratedRef.current = true;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!soundHydratedRef.current) return;
    try {
      localStorage.setItem(SOUND_PRESET_STORAGE_KEY, soundPreset);
    } catch {
      // Ignore quota/security errors.
    }
  }, [soundPreset]);

  // 19 kHz tone at a moderate level: Chrome sees a real audio stream (tab
  // speaker icon), while most speakers/headphones cannot reproduce it, so it
  // is effectively silent. A near-zero gain was treated as silence and the
  // tab was still throttled.
  const startKeepAlive = useCallback(() => {
    const ctx = ensureAudioContext();
    if (!ctx) return;
    void ctx.resume();
    if (keepAliveRef.current) return;
    const gain = ctx.createGain();
    gain.gain.value = 0.05;
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = 19000;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    keepAliveRef.current = { osc, gain };
  }, [ensureAudioContext]);

  const stopKeepAlive = useCallback(() => {
    const node = keepAliveRef.current;
    if (!node) return;
    try {
      node.osc.stop();
    } catch {
      // Already stopped; nothing to do.
    }
    node.osc.disconnect();
    node.gain.disconnect();
    keepAliveRef.current = null;
  }, []);

  useEffect(() => {
    if (backgroundMode) startKeepAlive();
    else stopKeepAlive();
  }, [backgroundMode, startKeepAlive, stopKeepAlive]);

  useEffect(
    () => () => {
      stopKeepAlive();
      void audioContextRef.current?.close();
      audioContextRef.current = null;
    },
    [stopKeepAlive]
  );

  // Returning to the foreground recomputes immediately instead of waiting for
  // the next (possibly throttled) tick.
  useEffect(() => {
    if (paused) return;
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        setNow(Math.floor(Date.now() / 1000));
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [paused]);

  useEffect(() => {
    if (now === null || paused || (!popupEnabled && !soundEnabled)) return;
    // Alert only for the queue and map picked in the controls above.
    const selectedMap = MAPS.find((map) => map.key === alertMapKey) ?? MAPS[0];
    const cycle = rotationSeconds * 3;
    const remaining = calculateCountdowns(
      selectedMap.offsetWindows,
      now,
      rotationSeconds
    )[alertMode];
    // 0 means the window just rolled over; the next window will trigger at
    // its own threshold instead.
    if (remaining <= 0 || remaining > alertSeconds) return;
    const startOfDay = new Date(now * 1000).setUTCHours(0, 0, 0, 0) / 1000;
    // Use the same -1 s shift as calculateCountdowns. Without it, the last
    // second before 0:00 falls into the next cycle index and fires a second
    // alert at rotation end.
    const shifted = now - startOfDay - 1;
    const cycleIndex = Math.floor(shifted / cycle);
    const windowIndex = Math.floor(
      (((shifted % cycle) + cycle) % cycle) / rotationSeconds
    );
    const key = `${cycleIndex}:${windowIndex}:${alertMode}:${alertMapKey}:${rotationSeconds}`;
    if (lastAlertKeyRef.current === key) return;
    lastAlertKeyRef.current = key;
    if (soundEnabled) playAlert();
    if (popupEnabled) {
      const body = ut('ui.timer.popup_body')
        .replace('{queue}', ut(`ui.timer.mode.${alertMode}`))
        .replace('{map}', ut(`ui.timer.map.${alertMapKey}`))
        .replace('{seconds}', String(remaining));
      if (
        typeof window !== 'undefined' &&
        'Notification' in window &&
        window.Notification.permission === 'granted'
      ) {
        // Chrome/Edge on Windows 11 show this as a native toast in the
        // bottom-right notification area.
        new window.Notification(ut('ui.timer.popup_title'), {
          body,
          tag: key,
          silent: true,
        });
      } else {
        setPopup({ mapKey: alertMapKey, mode: alertMode, seconds: remaining });
      }
    }
    // One-shot: clear both channels so the rest of the match stays quiet.
    setPopupEnabled(false);
    setSoundEnabled(false);
  }, [
    now,
    popupEnabled,
    soundEnabled,
    alertSeconds,
    alertMode,
    rotationSeconds,
    alertMapKey,
    paused,
    playAlert,
    ut,
  ]);

  useEffect(() => {
    if (paused) return;
    const tick = () => setNow(Math.floor(Date.now() / 1000));
    // Resuming ticks immediately, so the table jumps back to live values.
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [paused]);

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
  const previousColor = dark ? '#ffd54f' : '#f57f17';
  const previousBackground = dark
    ? 'rgba(255, 213, 79, 0.12)'
    : 'rgba(245, 127, 23, 0.12)';
  // For each mode the map with the largest countdown is the one that was open
  // in the previous rotation window; old rooms may still accept mid-run joins.
  const previousByMode: Record<Mode, string | null> = {
    solo: null,
    duo: null,
    trio: null,
  };
  if (now !== null) {
    for (const mode of MODES) {
      let previousKey: string | null = null;
      let previousValue = -1;
      for (const map of MAPS) {
        const value = calculateCountdowns(
          map.offsetWindows,
          now,
          rotationSeconds
        )[mode];
        if (value > previousValue) {
          previousValue = value;
          previousKey = map.key;
        }
      }
      previousByMode[mode] = previousKey;
    }
  }
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
          {ut('ui.timer.rotation_label')}
        </span>
        <Select
          value={
            (ROTATION_OPTIONS as readonly number[]).includes(rotationSeconds)
              ? rotationSeconds
              : 0
          }
          onChange={(value) => {
            if (value === 0) {
              setRotationCustom(true);
              return;
            }
            setRotationCustom(false);
            setRotationSeconds(value);
          }}
          aria-label={ut('ui.timer.rotation_label')}
          options={[
            { value: 180, label: ut('ui.timer.rotation_option.180') },
            { value: 240, label: ut('ui.timer.rotation_option.240') },
            { value: 300, label: ut('ui.timer.rotation_option.300') },
            { value: 0, label: ut('ui.timer.rotation_custom') },
          ]}
          style={{ width: 130 }}
        />
        {rotationCustom && (
          <>
            <InputNumber
              min={1}
              max={3600}
              value={rotationSeconds}
              onChange={(value) => {
                if (typeof value === 'number') setRotationSeconds(value);
              }}
              style={{ width: 120 }}
            />
            <span style={{ color: tokens.muted, fontSize: 12 }}>
              {ut('ui.timer.rotation_seconds')}
            </span>
          </>
        )}
        <span style={{ color: tokens.muted, fontSize: 12, flex: '1 1 240px' }}>
          {ut('ui.timer.rotation_hint')}
        </span>
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
        <span style={{ color: tokens.text, fontSize: 14 }}>
          {ut('ui.timer.alert_queue')}
        </span>
        <Select
          value={alertMode}
          onChange={setAlertMode}
          aria-label={ut('ui.timer.alert_queue')}
          options={ALERT_MODE_OPTIONS.map((mode) => ({
            value: mode,
            label: ut(`ui.timer.mode.${mode}`),
          }))}
          style={{ width: 130 }}
        />
        <span style={{ color: tokens.text, fontSize: 14 }}>
          {ut('ui.timer.alert_map')}
        </span>
        <Select
          value={alertMapKey}
          onChange={setAlertMapKey}
          aria-label={ut('ui.timer.alert_map')}
          options={MAPS.map((map) => ({
            value: map.key,
            label: ut(`ui.timer.map.${map.key}`),
          }))}
          style={{ width: 120 }}
        />
        <span style={{ flexBasis: '100%', height: 0 }} />
        <span style={{ color: tokens.text, fontSize: 14 }}>
          {ut('ui.timer.alert_seconds_label')}
        </span>
        <AutoComplete
          className="alert-seconds-input"
          value={alertSecondsText}
          options={ALERT_OPTIONS.map((value) => ({
            value: String(value),
          }))}
          onChange={(text) => {
            const digits = text.replace(/\D/g, '');
            setAlertSecondsText(digits);
            const parsed = Number(digits);
            if (digits && parsed > 0) setAlertSeconds(parsed);
          }}
          onBlur={() => {
            setAlertSecondsText((text) => {
              const parsed = Number(text);
              return text && parsed > 0 ? String(parsed) : String(alertSeconds);
            });
          }}
          aria-label={ut('ui.timer.alert_seconds_label')}
          style={{ width: 110 }}
        />
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            color: tokens.text,
            fontSize: 14,
          }}
        >
          {ut('ui.timer.popup_checkbox')}
          <Switch
            checked={popupEnabled}
            onChange={(checked) => {
              setPopupEnabled(checked);
              // Ask for permission inside the click gesture; if it is denied
              // or unsupported the in-page modal remains the fallback.
              if (
                checked &&
                typeof window !== 'undefined' &&
                'Notification' in window &&
                window.Notification.permission === 'default'
              ) {
                void window.Notification.requestPermission();
              }
            }}
          />
        </span>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            color: tokens.text,
            fontSize: 14,
          }}
        >
          {ut('ui.timer.sound_checkbox')}
          <Switch
            checked={soundEnabled}
            onChange={(checked) => {
              setSoundEnabled(checked);
              // Creating/resuming here keeps the later automatic alert inside
              // the browser's user-gesture policy.
              if (checked) ensureAudioContext();
            }}
          />
        </span>
        <Select
          value={soundPreset}
          onChange={(value: SoundPreset) => {
            setSoundPreset(value);
            setSoundEnabled(true);
            ensureAudioContext();
            playSound(value, value === 'custom' ? customAudioUrl : null);
          }}
          aria-label={ut('ui.timer.sound_checkbox')}
          options={SOUND_PRESETS.map((preset) => ({
            value: preset,
            label: ut(`ui.timer.sound_preset.${preset}`),
          }))}
          style={{ width: 150 }}
        />
        {soundPreset === 'custom' && (
          <>
            <Button
              size="small"
              onClick={() => soundFileInputRef.current?.click()}
            >
              {ut('ui.timer.sound_upload')}
            </Button>
            <input
              ref={soundFileInputRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={handleSoundFile}
            />
            <span style={{ color: tokens.muted, fontSize: 12 }}>
              {customAudioName || ut('ui.timer.sound_no_file')}
            </span>
            <span
              style={{
                color: tokens.muted,
                fontSize: 12,
                flexBasis: '100%',
              }}
            >
              {ut('ui.timer.sound_upload_hint')}
            </span>
          </>
        )}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            color: tokens.text,
            fontSize: 14,
          }}
        >
          {ut('ui.timer.background_label')}
          <Switch
            checked={backgroundMode}
            onChange={(checked) => setBackgroundMode(checked)}
          />
        </span>
        <span style={{ color: tokens.muted, fontSize: 12, flex: '1 1 320px' }}>
          {ut(
            backgroundMode
              ? 'ui.timer.background_on_hint'
              : 'ui.timer.background_off_hint'
          )}
        </span>
        <span style={{ flexBasis: '100%', height: 0 }} />
        <span style={{ color: tokens.muted, fontSize: 12, flex: '1 1 100%' }}>
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
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 8,
                }}
              >
                <span>
                  {ut('ui.timer.local_time')}:{' '}
                  <span style={{ color: tokens.accent }}>
                    {now === null ? '--:--:--' : formatLocalClock(now)}
                  </span>
                </span>
                <Button
                  size="small"
                  autoInsertSpace={false}
                  onClick={() => setPaused((value) => !value)}
                >
                  {paused ? ut('ui.timer.resume') : ut('ui.timer.pause')}
                </Button>
              </div>
              {paused && (
                <div style={{ color: tokens.muted, fontSize: 11 }}>
                  {ut('ui.timer.paused_hint')}
                </div>
              )}
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
              now === null
                ? null
                : calculateCountdowns(map.offsetWindows, now, rotationSeconds);
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
                  const open =
                    seconds !== undefined && seconds < rotationSeconds;
                  const inAlertWindow =
                    open && seconds !== undefined && seconds <= alertSeconds;
                  const isPrevious = previousByMode[mode] === map.key;
                  const highlightColor = inAlertWindow
                    ? alertColor
                    : open
                      ? openColor
                      : isPrevious
                        ? previousColor
                        : tokens.text;
                  const highlightBackground = inAlertWindow
                    ? alertBackground
                    : open
                      ? openBackground
                      : isPrevious
                        ? previousBackground
                        : 'transparent';
                  return (
                    <div
                      key={mode}
                      style={{
                        padding: '10px 6px',
                        textAlign: 'center',
                        background: highlightBackground,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 22,
                          fontWeight: 700,
                          fontVariantNumeric: 'tabular-nums',
                          color: highlightColor,
                        }}
                      >
                        {seconds === undefined ? '--:--' : formatTime(seconds)}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: highlightColor,
                          minHeight: 14,
                        }}
                      >
                        {inAlertWindow
                          ? ut('ui.timer.final_window')
                          : open
                            ? ut('ui.timer.open')
                            : isPrevious
                              ? ut('ui.timer.previous_window')
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

      <Modal
        open={popup !== null}
        title={ut('ui.timer.popup_title')}
        onOk={() => setPopup(null)}
        onCancel={() => setPopup(null)}
        okText={ut('ui.timer.popup_close')}
        cancelButtonProps={{ style: { display: 'none' } }}
        centered
      >
        {popup === null
          ? null
          : ut('ui.timer.popup_body')
              .replace('{queue}', ut(`ui.timer.mode.${popup.mode}`))
              .replace('{map}', ut(`ui.timer.map.${popup.mapKey}`))
              .replace('{seconds}', String(popup.seconds))}
      </Modal>
    </div>
  );
}
