import { useEffect, useRef, useState, type CSSProperties } from 'react';
import {
  DeleteOutlined,
  DownloadOutlined,
  PictureOutlined,
  ScanOutlined,
} from '@ant-design/icons';
import type { CV } from '@techstark/opencv-js';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import {
  decodeScreenshot,
  loadMapImageTemplates,
  loadOpenCv,
  recognizeMapScreenshot,
  type LoadedMapImageTemplate,
  type MapImageTemplate,
  type MapImageMatch,
} from '../utils/mapImageRecognition';

interface MapImageRecognitionProps {
  templates: MapImageTemplate[];
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
}

type RecognitionStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'recognizing'
  | 'done'
  | 'error';

const switchTrack: CSSProperties = {
  position: 'relative',
  display: 'inline-block',
  width: 34,
  height: 18,
  flexShrink: 0,
};

export default function MapImageRecognition({
  templates,
  enabled,
  onEnabledChange,
}: MapImageRecognitionProps) {
  const { tokens } = useTheme();
  const { ut } = useLocale();
  const utRef = useRef(ut);
  const templatesRef = useRef(templates);
  const cvRef = useRef<CV | null>(null);
  const loadedTemplatesRef = useRef<LoadedMapImageTemplate[]>([]);
  const previewUrlRef = useRef<string | null>(null);
  const pasteAreaRef = useRef<HTMLDivElement>(null);
  const templateSignature = templates
    .map((template) => `${template.id}:${template.url}:${template.label}`)
    .join('|');
  const [status, setStatus] = useState<RecognitionStatus>('idle');
  const [templateProgress, setTemplateProgress] = useState({
    loaded: 0,
    total: 0,
  });
  const [templateCount, setTemplateCount] = useState(0);
  const [templateFailures, setTemplateFailures] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [matches, setMatches] = useState<MapImageMatch[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  templatesRef.current = templates;
  utRef.current = ut;

  useEffect(() => {
    if (!enabled) {
      setStatus('idle');
      setTemplateProgress({ loaded: 0, total: 0 });
      setTemplateCount(0);
      setTemplateFailures(0);
      setErrorMessage(null);
      return;
    }

    let cancelled = false;
    const currentTemplates = templatesRef.current;
    setStatus('loading');
    setErrorMessage(null);
    setTemplateProgress({ loaded: 0, total: currentTemplates.length });

    Promise.all([
      loadOpenCv(),
      loadMapImageTemplates(currentTemplates, (loaded, total) => {
        if (!cancelled) setTemplateProgress({ loaded, total });
      }),
    ])
      .then(([cv, loaded]) => {
        if (cancelled) return;
        cvRef.current = cv;
        loadedTemplatesRef.current = loaded.templates;
        setTemplateCount(loaded.templates.length);
        setTemplateFailures(loaded.failed);
        if (loaded.templates.length === 0) {
          setStatus('error');
          setErrorMessage(utRef.current('ui.map_recognition.no_templates'));
          return;
        }
        setStatus('ready');
      })
      .catch(() => {
        if (cancelled) return;
        setStatus('error');
        setErrorMessage(utRef.current('ui.map_recognition.engine_error'));
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, templateSignature]);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  function clearResult() {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = null;
    setPreviewUrl(null);
    setMatches([]);
    setErrorMessage(null);
    if (enabled && cvRef.current && loadedTemplatesRef.current.length > 0) {
      setStatus('ready');
    }
  }

  function handleEnabledChange(nextEnabled: boolean) {
    if (!nextEnabled) clearResult();
    onEnabledChange(nextEnabled);
  }

  async function handlePaste(event: React.ClipboardEvent<HTMLDivElement>) {
    event.preventDefault();
    const imageItem = [...event.clipboardData.items].find((item) =>
      item.type.startsWith('image/')
    );
    if (!imageItem) {
      setStatus('error');
      setErrorMessage(ut('ui.map_recognition.image_required'));
      return;
    }
    const blob = imageItem.getAsFile();
    const cv = cvRef.current;
    if (!blob || !cv || loadedTemplatesRef.current.length === 0) {
      setStatus('error');
      setErrorMessage(ut('ui.map_recognition.not_ready'));
      return;
    }

    setStatus('recognizing');
    setErrorMessage(null);
    try {
      const screenshot = await decodeScreenshot(blob);
      const output = await recognizeMapScreenshot(
        screenshot,
        loadedTemplatesRef.current,
        cv
      );
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      const nextPreviewUrl = URL.createObjectURL(output.blob);
      previewUrlRef.current = nextPreviewUrl;
      setPreviewUrl(nextPreviewUrl);
      setMatches(output.matches);
      setStatus('done');
    } catch {
      setStatus('error');
      setErrorMessage(ut('ui.map_recognition.recognition_error'));
    }
  }

  const statusText =
    status === 'loading'
      ? ut('ui.map_recognition.loading')
      : status === 'recognizing'
        ? ut('ui.map_recognition.recognizing')
        : status === 'error'
          ? errorMessage || ut('ui.map_recognition.engine_error')
          : status === 'done'
            ? matches.length > 0
              ? ut('ui.map_recognition.match_count').replace(
                  '{count}',
                  String(matches.length)
                )
              : ut('ui.map_recognition.no_match')
            : status === 'ready'
              ? ut('ui.map_recognition.ready')
              : ut('ui.map_recognition.paste_area');

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
        <span style={switchTrack}>
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

      {enabled && (
        <div
          style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            paddingTop: 8,
            borderTop: `1px solid ${tokens.border}`,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
              color: tokens.text,
            }}
          >
            <span
              style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}
            >
              <ScanOutlined />
              {ut('ui.map_recognition.title')}
            </span>
            <span style={{ color: tokens.muted, fontSize: 11 }}>
              {ut('ui.map_recognition.template_count').replace(
                '{count}',
                String(templateCount)
              )}
            </span>
          </div>

          <div
            ref={pasteAreaRef}
            tabIndex={0}
            role="button"
            aria-label={ut('ui.map_recognition.paste_area')}
            onClick={() => pasteAreaRef.current?.focus()}
            onPaste={handlePaste}
            style={{
              minHeight: previewUrl ? undefined : 84,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 5,
              padding: 8,
              border: `1px dashed ${status === 'error' ? '#d14343' : tokens.border}`,
              borderRadius: 4,
              color: status === 'error' ? '#d14343' : tokens.muted,
              background: tokens.bg,
              cursor: 'text',
              outline: 'none',
            }}
          >
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={ut('ui.map_recognition.preview_alt')}
                style={{
                  display: 'block',
                  width: '100%',
                  maxHeight: 460,
                  objectFit: 'contain',
                }}
              />
            ) : (
              <PictureOutlined style={{ fontSize: 24 }} />
            )}
            <span role="status" aria-live="polite" style={{ fontSize: 12 }}>
              {statusText}
            </span>
          </div>

          {status === 'loading' && (
            <div
              style={{ color: tokens.muted, fontSize: 11, textAlign: 'center' }}
            >
              {ut('ui.map_recognition.template_progress')
                .replace('{loaded}', String(templateProgress.loaded))
                .replace('{total}', String(templateProgress.total))}
            </div>
          )}

          {templateFailures > 0 && status !== 'error' && (
            <div
              style={{ color: tokens.muted, fontSize: 11, textAlign: 'center' }}
            >
              {ut('ui.map_recognition.template_failed').replace(
                '{count}',
                String(templateFailures)
              )}
            </div>
          )}

          {previewUrl && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 8,
                flexWrap: 'wrap',
              }}
            >
              <a
                href={previewUrl}
                download="darkfind-map-recognition.png"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 8px',
                  border: `1px solid ${tokens.border}`,
                  borderRadius: 3,
                  color: tokens.text,
                  textDecoration: 'none',
                  fontSize: 12,
                }}
              >
                <DownloadOutlined />
                {ut('ui.map_recognition.export')}
              </a>
              <button
                type="button"
                onClick={clearResult}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 8px',
                  border: `1px solid ${tokens.border}`,
                  borderRadius: 3,
                  color: tokens.text,
                  background: 'transparent',
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                <DeleteOutlined />
                {ut('ui.map_recognition.clear')}
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
