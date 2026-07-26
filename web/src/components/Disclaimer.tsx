import type { CSSProperties } from 'react';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';

export default function Disclaimer() {
  const { tokens } = useTheme();
  const date = useDataVersion();
  const { ut } = useLocale();
  const box: CSSProperties = {
    textAlign: 'center',
    color: '#ff6b6b',
    fontSize: 14,
    marginBottom: 12,
    padding: 6,
    background: tokens.surface,
    borderRadius: 5,
    maxWidth: 700,
    marginLeft: 'auto',
    marginRight: 'auto',
  };

  const formattedDate = date
    ? /^\d{8}$/.test(date)
      ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
      : new Date(Number(date) * 1000).toISOString().slice(0, 10)
    : '';

  return (
    <div style={box}>
      ⚠️ {ut('ui.disclaimer.warning')}
      <span style={{ color: tokens.muted, marginLeft: 15 }}>
        {ut('ui.disclaimer.data_date').replace('{date}', formattedDate)}
        <a
          href="https://www.bilibili.com/video/BV1isKE68EP5"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: tokens.accent,
            textDecoration: 'none',
            fontSize: 'inherit',
          }}
        >
          【{ut('ui.disclaimer.feedback')}】
        </a>
      </span>
    </div>
  );
}
