import { lazy, Suspense, useState } from 'react';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import type { MapImageTemplate } from '../utils/mapImageRecognition';

interface MapImageRecognitionProps {
  templates: MapImageTemplate[];
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
}

const MapImageRecognitionPanel = lazy(
  () => import('./MapImageRecognitionPanel')
);

export default function MapImageRecognition({
  templates,
  enabled,
  onEnabledChange,
}: MapImageRecognitionProps) {
  const { tokens } = useTheme();
  const { ut } = useLocale();
  const [panelRequested, setPanelRequested] = useState(enabled);

  function handleEnabledChange(nextEnabled: boolean) {
    if (nextEnabled) setPanelRequested(true);
    else setPanelRequested(false);
    onEnabledChange(nextEnabled);
  }

  return (
    <>
      <label
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <span>{ut('ui.map_recognition.toggle')}</span>
        <span
          style={{
            position: 'relative',
            display: 'inline-block',
            width: 34,
            height: 18,
            flexShrink: 0,
          }}
        >
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => handleEnabledChange(event.target.checked)}
            aria-label={ut('ui.map_recognition.toggle')}
            style={{
              position: 'absolute',
              width: 1,
              height: 1,
              opacity: 0,
              margin: 0,
            }}
          />
          <span
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: 9,
              background: enabled ? '#39a96b' : tokens.border,
              transition: 'background 0.2s',
            }}
          />
          <span
            aria-hidden="true"
            style={{
              position: 'absolute',
              top: 3,
              left: enabled ? 19 : 3,
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#fff',
              boxShadow: '0 1px 2px rgba(0,0,0,0.35)',
              transition: 'left 0.2s',
            }}
          />
        </span>
      </label>
      {enabled && panelRequested && (
        <Suspense fallback={null}>
          <MapImageRecognitionPanel templates={templates} enabled={enabled} />
        </Suspense>
      )}
    </>
  );
}
