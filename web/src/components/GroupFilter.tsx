import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';

export interface GroupOption {
  /** Raw group id (``mod.group``), used as the select value. */
  name: string;
  /** Localized label shown to the user. */
  label: string;
}

type Props = {
  groups: GroupOption[];
  /** Selected group name, or '' for every group. */
  value: string;
  onChange: (group: string) => void;
};

/**
 * Alphabetical order by label, with digit runs compared numerically so the
 * floors of one dungeon stay together ("废墟1层 / 废墟2层 / 废墟3层").
 *
 * Deliberately avoids Intl.Collator: the options are server-rendered, and a
 * collator whose ICU differs between Node and the browser would reorder the
 * <option> list during hydration.
 */
function compareGroupLabels(a: string, b: string): number {
  const pa = a.match(/\d+|\D+/g) ?? [];
  const pb = b.match(/\d+|\D+/g) ?? [];
  for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
    const x = pa[i];
    const y = pb[i];
    if (x === y) continue;
    const nx = /^\d+$/.test(x);
    const ny = /^\d+$/.test(y);
    if (nx && ny) return Number(x) - Number(y);
    return x < y ? -1 : 1;
  }
  return pa.length - pb.length;
}

function sortGroups(groups: GroupOption[]): GroupOption[] {
  return [...groups].sort((a, b) => compareGroupLabels(a.label, b.label));
}

/**
 * "地图分组显示" picker, shown above the map grid on entity and loot pages.
 * Deliberately always visible (not tucked into the debug panel): narrowing the
 * page to one dungeon is useful to everyone, not just when debugging.
 */
export default function GroupFilter({ groups, value, onChange }: Props) {
  const { tokens } = useTheme();
  const { ut } = useLocale();
  if (groups.length < 2) return null;
  const sorted = sortGroups(groups);

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        margin: '10px 0',
        padding: '6px 10px',
        background: tokens.surface,
        borderRadius: 5,
        fontSize: 13,
        color: tokens.text,
      }}
    >
      <span style={{ color: tokens.muted }}>{ut('ui.filter.group')}：</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={ut('ui.filter.group')}
        style={{
          background: tokens.bg,
          color: tokens.text,
          border: `1px solid ${tokens.border}`,
          borderRadius: 4,
          padding: '2px 6px',
          fontSize: 13,
          cursor: 'pointer',
        }}
      >
        <option value="">{ut('ui.filter.all_groups')}</option>
        {sorted.map((group) => (
          <option key={group.name} value={group.name}>
            {group.label}
          </option>
        ))}
      </select>
    </div>
  );
}
