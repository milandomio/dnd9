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
  type MapImageRecognitionDebug,
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

type PrecisionPreset = 'standard' | 'high' | 'maximum' | 'custom';

const PRECISION_PRESETS: Record<Exclude<PrecisionPreset, 'custom'>, number> = {
  standard: 0.52,
  high: 0.45,
  maximum: 0.38,
};

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
  const [selectedGroup, setSelectedGroup] = useState('');
  const [precisionPreset, setPrecisionPreset] =
    useState<PrecisionPreset>('standard');
  const [thresholdInput, setThresholdInput] = useState('0.52');
  const groupOptions = [
    ...new Map(
      templates
        .filter((template) => template.group)
        .map((template) => [template.group, template.groupLabel])
    ).entries(),
  ].sort((a, b) => a[1].localeCompare(b[1]));
  const activeTemplates = selectedGroup
    ? templates.filter((template) => template.group === selectedGroup)
    : templates;
  const templatesRef = useRef(activeTemplates);
  const cvRef = useRef<CV | null>(null);
  const loadedTemplatesRef = useRef<LoadedMapImageTemplate[]>([]);
  const previewUrlRef = useRef<string | null>(null);
  const pasteAreaRef = useRef<HTMLDivElement>(null);
  const templateSignature = activeTemplates
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
  const [gridType, setGridType] = useState<'5x5' | '7x7' | null>(null);
  const [debugData, setDebugData] = useState<MapImageRecognitionDebug | null>(
    null
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  templatesRef.current = activeTemplates;
  utRef.current = ut;

  useEffect(() => {
    if (
      selectedGroup &&
      !templates.some((template) => template.group === selectedGroup)
    ) {
      setSelectedGroup('');
    }
  }, [selectedGroup, templates]);

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
    loadedTemplatesRef.current = [];
    setStatus('loading');
    setErrorMessage(null);
    setTemplateCount(0);
    setTemplateFailures(0);
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
    setGridType(null);
    setDebugData(null);
    setErrorMessage(null);
    if (enabled && cvRef.current && loadedTemplatesRef.current.length > 0) {
      setStatus('ready');
    }
  }

  function handleEnabledChange(nextEnabled: boolean) {
    if (!nextEnabled) clearResult();
    onEnabledChange(nextEnabled);
  }

  function handleGroupChange(group: string) {
    clearResult();
    setSelectedGroup(group);
  }

  function handlePrecisionPreset(preset: PrecisionPreset) {
    setPrecisionPreset(preset);
    if (preset !== 'custom') {
      setThresholdInput(PRECISION_PRESETS[preset].toFixed(2));
    }
  }

  function handleThresholdChange(value: string) {
    setThresholdInput(value);
    setPrecisionPreset('custom');
  }

  function normalizeThreshold() {
    const threshold = Number(thresholdInput);
    const normalized = Number.isFinite(threshold)
      ? Math.min(0.9, Math.max(0.2, threshold))
      : PRECISION_PRESETS.standard;
    setThresholdInput(normalized.toFixed(2));
    return normalized;
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
        cv,
        { threshold: normalizeThreshold(), group: selectedGroup || undefined }
      );
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      const nextPreviewUrl = URL.createObjectURL(output.blob);
      previewUrlRef.current = nextPreviewUrl;
      setPreviewUrl(nextPreviewUrl);
      setMatches(output.matches);
      setGridType(output.gridType);
      setDebugData(output.debug);
      setStatus('done');
    } catch {
      setStatus('error');
      setErrorMessage(ut('ui.map_recognition.recognition_error'));
    }
  }

  function exportDebugData() {
    if (!debugData) return;
    const blob = new Blob([JSON.stringify(debugData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'darkfind-map-recognition-debug.json';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const baseStatusText =
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
  const statusText =
    status === 'done' && gridType
      ? `${baseStatusText} · ${ut('ui.map_recognition.grid_type').replace('{grid}', gridType)}`
      : baseStatusText;

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
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <select
                aria-label={ut('ui.map_recognition.group_select')}
                value={selectedGroup}
                onChange={(event) => handleGroupChange(event.target.value)}
                style={{
                  maxWidth: 180,
                  padding: '2px 5px',
                  border: `1px solid ${tokens.border}`,
                  borderRadius: 3,
                  color: tokens.text,
                  background: tokens.bg,
                  fontSize: 11,
                }}
              >
                <option value="">{ut('ui.filter.all')}</option>
                {groupOptions.map(([group, label]) => (
                  <option key={group} value={group}>
                    {label}
                  </option>
                ))}
              </select>
              <span style={{ color: tokens.muted, fontSize: 11 }}>
                {ut('ui.map_recognition.template_count').replace(
                  '{count}',
                  String(templateCount)
                )}
              </span>
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              flexWrap: 'wrap',
              color: tokens.muted,
              fontSize: 11,
            }}
          >
            <label
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              {ut('ui.map_recognition.precision')}
              <select
                aria-label={ut('ui.map_recognition.precision')}
                value={precisionPreset}
                onChange={(event) =>
                  handlePrecisionPreset(event.target.value as PrecisionPreset)
                }
                style={{
                  padding: '2px 5px',
                  border: `1px solid ${tokens.border}`,
                  borderRadius: 3,
                  color: tokens.text,
                  background: tokens.bg,
                  fontSize: 11,
                }}
              >
                <option value="standard">
                  {ut('ui.map_recognition.precision_standard')}
                </option>
                <option value="high">
                  {ut('ui.map_recognition.precision_high')}
                </option>
                <option value="maximum">
                  {ut('ui.map_recognition.precision_maximum')}
                </option>
                <option value="custom">
                  {ut('ui.map_recognition.precision_custom')}
                </option>
              </select>
            </label>
            <label
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              {ut('ui.map_recognition.threshold')}
              <input
                type="number"
                aria-label={ut('ui.map_recognition.threshold')}
                min={0.2}
                max={0.9}
                step={0.01}
                value={thresholdInput}
                onChange={(event) => handleThresholdChange(event.target.value)}
                onBlur={normalizeThreshold}
                style={{
                  width: 58,
                  padding: '2px 4px',
                  border: `1px solid ${tokens.border}`,
                  borderRadius: 3,
                  color: tokens.text,
                  background: tokens.bg,
                  fontSize: 11,
                }}
              />
            </label>
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

          {matches.length > 0 && (
            <details
              open
              style={{
                border: `1px solid ${tokens.border}`,
                borderRadius: 4,
                color: tokens.text,
                fontSize: 11,
              }}
            >
              <summary
                style={{
                  padding: '6px 8px',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                {ut('ui.map_recognition.result_details')}
              </summary>
              <div
                style={{
                  display: 'grid',
                  gap: 1,
                  borderTop: `1px solid ${tokens.border}`,
                  background: tokens.border,
                }}
              >
                {matches.map((match, index) => (
                  <div
                    key={`${match.templateId}-${match.x}-${match.y}-${index}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(100px, 1fr) auto',
                      gap: 8,
                      padding: '6px 8px',
                      background: tokens.bg,
                    }}
                  >
                    <span style={{ overflowWrap: 'anywhere' }}>
                      {index + 1}. {match.label}
                    </span>
                    <span
                      style={{
                        color: tokens.muted,
                        textAlign: 'right',
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {match.method === 'template-inner'
                        ? `${ut('ui.map_recognition.method_template')} (inner)`
                        : ut(`ui.map_recognition.method_${match.method}`)}{' '}
                      · {match.score.toFixed(3)}
                      <br />x {Math.round(match.x)}, y {Math.round(match.y)}, w{' '}
                      {Math.round(match.width)}, h {Math.round(match.height)}
                    </span>
                  </div>
                ))}
              </div>
            </details>
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
              {debugData && (
                <button
                  type="button"
                  onClick={exportDebugData}
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
                  <DownloadOutlined />
                  {ut('ui.map_recognition.export_debug')}
                </button>
              )}
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
