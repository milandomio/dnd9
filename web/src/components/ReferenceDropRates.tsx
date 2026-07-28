import { useLocale } from '../i18n/useLocale';
import {
  formatDropRateEntryLabel,
  formatDropRateSuffix,
  type DropRateEntry,
} from '../utils/dropRate';

export type { DropRateEntry };

interface ReferenceDropRatesProps {
  entries: DropRateEntry[];
  modeFilter?: string;
  adjSpawnRate?: (v: number) => number;
  /** show「参考爆率：」prefix (group header); false for module legend */
  showPrefix?: boolean;
  /** wrap mode list in () when single spawn_rate (module style) */
  parenModes?: boolean;
  labelSeparator?: string;
  style?: React.CSSProperties;
  entryStyle?: React.CSSProperties;
}

export default function ReferenceDropRates({
  entries,
  modeFilter,
  adjSpawnRate,
  showPrefix = true,
  parenModes = false,
  labelSeparator,
  style,
  entryStyle,
}: ReferenceDropRatesProps) {
  const { t, ut } = useLocale();
  if (!entries.length) return null;

  return (
    <span style={style}>
      {showPrefix ? ut('ui.detail.ref_rate') : null}
      {entries.map((info, gi) => (
        <span
          key={gi}
          style={{
            display: 'inline-block',
            marginRight: 8,
            ...entryStyle,
          }}
        >
          {formatDropRateEntryLabel(info, t, ut)}
          {labelSeparator}
          {formatDropRateSuffix(info, t, ut, {
            modeFilter,
            adjSpawnRate,
            parenModes,
          })}
        </span>
      ))}
    </span>
  );
}
