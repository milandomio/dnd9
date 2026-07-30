import type { CSSProperties } from 'react';
import { useLocale } from '../i18n/useLocale';
import { useTheme } from '../hooks/useTheme';

interface CompositeRateProps {
  rate: number;
  spawnRate?: number;
  style?: CSSProperties;
  labelKey?: string;
  precision?: number;
  spawnPrecision?: number;
}

export default function CompositeRate({
  rate,
  spawnRate,
  style,
  labelKey = 'ui.detail.composite_rate',
  precision = 4,
  spawnPrecision = 2,
}: CompositeRateProps) {
  const { ut } = useLocale();
  const { tokens } = useTheme();
  if (rate <= 0 && (!spawnRate || spawnRate <= 0)) return null;

  const rateStyle = {
    marginTop: 4,
    fontSize: 12,
    textAlign: 'center' as const,
    color: tokens.accent,
    ...style,
  };

  return (
    <>
      {spawnRate && spawnRate > 0 && (
        <div style={rateStyle}>
          {ut('ui.detail.composite_spawn_rate')}{' '}
          {parseFloat(spawnRate.toFixed(spawnPrecision))}%
        </div>
      )}
      {rate > 0 && (
        <div style={rateStyle}>
          {ut(labelKey)} {parseFloat(rate.toFixed(precision))}%
        </div>
      )}
    </>
  );
}
