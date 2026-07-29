import type { CSSProperties } from 'react';
import { useLocale } from '../i18n/useLocale';
import { useTheme } from '../hooks/useTheme';

interface CompositeRateProps {
  rate: number;
  style?: CSSProperties;
}

export default function CompositeRate({ rate, style }: CompositeRateProps) {
  const { ut } = useLocale();
  const { tokens } = useTheme();
  if (rate <= 0) return null;

  return (
    <div
      style={{
        marginTop: 4,
        fontSize: 12,
        textAlign: 'center',
        color: tokens.accent,
        ...style,
      }}
    >
      {ut('ui.detail.composite_rate')} {parseFloat(rate.toFixed(4))}%
    </div>
  );
}
