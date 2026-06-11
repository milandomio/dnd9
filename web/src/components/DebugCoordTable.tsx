import { type CSSProperties } from 'react';
import { useTheme } from '../hooks/useTheme';

export interface CoordRow {
  /** Unique row key (e.g. "monsterName-0") */
  key: string;
  /** Group display name */
  group: string;
  /** Original group machine name (for toggling) */
  groupKey?: string;
  /** Optional monster/entity name column (omit for single-entity pages) */
  monster?: {
    name: string;
    translation: string;
    color: string;
    onToggle?: () => void;
  };
  /** Map JSON filename */
  file: string;
  /** Map identifier for grouping toggle */
  mapName: string;
  /** Map translation */
  mapLabel: string;
  /** Spawner original keyword / label */
  label: string;
  /** Coordinates */
  x: number;
  y: number;
  z: number;
  /** Whether this row is hidden */
  hidden: boolean;
}

const checkTdBase: CSSProperties = {
  width: 24,
  textAlign: 'center',
  verticalAlign: 'middle',
};

const checkboxStyle: CSSProperties = {
  accentColor: '#00bcd4',
  cursor: 'pointer',
  margin: 0,
};
function cleanLabel(raw: string): string {
  return raw.replace(/^GameSpawner_/, '').replace(/^GameItemSpawner_/, '');
}

interface Props {
  rows: CoordRow[];
  onToggleRow: (key: string) => void;
  onToggleGroup?: (groupKey: string) => void;
  onToggleMarkName?: (monsterName: string) => void;
  onToggleFile?: (file: string) => void;
  onToggleMap?: (mapName: string) => void;
  onToggleLabel?: (label: string) => void;
  /** Show monster column (for multi-monster pages like lootdrops) */
  showMonster?: boolean;
}

export default function DebugCoordTable({
  rows,
  onToggleRow,
  onToggleGroup,
  onToggleMarkName,
  onToggleFile,
  onToggleMap,
  onToggleLabel,
  showMonster,
}: Props) {
  const { tokens } = useTheme();

  const th: CSSProperties = {
    padding: '4px 6px',
    borderBottom: `1px solid ${tokens.border}`,
    textAlign: 'center',
    verticalAlign: 'middle',
  };
  const td: CSSProperties = {
    padding: '3px 6px',
    borderBottom: `1px solid ${tokens.border}`,
    textAlign: 'center',
    alignContent: 'center',
  };
  const checkTd: CSSProperties = {
    ...td,
    ...checkTdBase,
  };
  // Helper: whether ALL matched rows are visible (none hidden)
  const allVisible = (pred: (r: CoordRow) => boolean) => {
    const matched = rows.filter(pred);
    return matched.length > 0 && matched.every((r) => !r.hidden);
  };
  // Whether ALL rows are hidden
  const allRowsHidden = rows.length > 0 && rows.every((r) => r.hidden);

  function colToggle(pred: (r: CoordRow) => boolean) {
    const matched = rows.filter(pred);
    if (matched.length === 0) return;
    const hideAll = matched.some((r) => !r.hidden);
    for (const r of matched) {
      if (hideAll && !r.hidden) onToggleRow(r.key);
      else if (!hideAll && r.hidden) onToggleRow(r.key);
    }
  }

  // ── Cell-level checkbox ──
  function CellChk({
    visible,
    onToggle,
  }: {
    visible: boolean;
    onToggle: () => void;
  }) {
    return (
      <input
        type="checkbox"
        checked={visible}
        onChange={onToggle}
        style={checkboxStyle}
      />
    );
  }

  return (
    <div
      style={{
        marginTop: 12,
        background: tokens.surface,
        borderRadius: 5,
        padding: 10,
        overflowX: 'auto',
      }}
    >
      <h3
        style={{
          textAlign: 'center',
          color: '#00bcd4',
          fontSize: 18,
          margin: '0 0 10px',
        }}
      >
        所有坐标详情
      </h3>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 13,
          color: tokens.muted,
        }}
      >
        <thead>
          <tr style={{ background: tokens.border, fontWeight: 'bold' }}>
            <th style={checkTd}>
              <input
                type="checkbox"
                checked={!allRowsHidden}
                onChange={() => colToggle(() => true)}
                style={checkboxStyle}
              />
            </th>
            <th style={th}>分组</th>
            {showMonster && <th style={th}>坐标名称</th>}
            <th style={th}>地图文件</th>
            <th style={th}>地图</th>
            <th style={th}>标签</th>
            <th style={th}>X</th>
            <th style={th}>Y</th>
            <th style={th}>Z</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const isHidden = row.hidden;
            return (
              <tr
                key={row.key}
                style={{
                  background: isHidden
                    ? tokens.bg
                    : idx % 2 === 0
                      ? tokens.surface
                      : tokens.card,
                  opacity: isHidden ? 0.3 : 1,
                }}
              >
                <td style={checkTd}>
                  <input
                    type="checkbox"
                    checked={!isHidden}
                    onChange={() => onToggleRow(row.key)}
                    style={checkboxStyle}
                  />
                </td>
                {/* 分组 */}
                <td style={td}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <CellChk
                      visible={allVisible(
                        (r) =>
                          (r.groupKey ?? r.group) ===
                          (row.groupKey ?? row.group)
                      )}
                      onToggle={() => {
                        const gk = row.groupKey ?? row.group;
                        if (onToggleGroup) onToggleGroup(gk);
                        else colToggle((r) => (r.groupKey ?? r.group) === gk);
                      }}
                    />
                    {row.group}
                  </span>
                </td>
                {/* 怪物 */}
                {showMonster && row.monster && (
                  <td style={td}>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <CellChk
                        visible={allVisible(
                          (r) => r.monster?.name === row.monster?.name
                        )}
                        onToggle={() => {
                          const name = row.monster?.name || '';
                          if (onToggleMarkName) onToggleMarkName(name);
                          else colToggle((r) => r.monster?.name === name);
                        }}
                      />
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: row.monster.color,
                          display: 'inline-block',
                          flexShrink: 0,
                        }}
                      ></span>
                      {row.monster.translation}
                    </span>
                  </td>
                )}
                {/* 地图文件 */}
                <td style={td}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <CellChk
                      visible={allVisible((r) => r.file === row.file)}
                      onToggle={() => {
                        if (onToggleFile) onToggleFile(row.file);
                        else colToggle((r) => r.file === row.file);
                      }}
                    />
                    {row.file}
                  </span>
                </td>
                {/* 地图 */}
                <td style={td}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <CellChk
                      visible={allVisible((r) => r.mapName === row.mapName)}
                      onToggle={() => {
                        if (onToggleMap) onToggleMap(row.mapName);
                        else colToggle((r) => r.mapName === row.mapName);
                      }}
                    />
                    {row.mapLabel}
                  </span>
                </td>
                {/* 标签 */}
                <td style={{ ...td, fontSize: 11 }}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <CellChk
                      visible={allVisible((r) => r.label === row.label)}
                      onToggle={() => {
                        if (onToggleLabel) onToggleLabel(row.label);
                        else colToggle((r) => r.label === row.label);
                      }}
                    />
                    {cleanLabel(row.label)}
                  </span>
                </td>
                <td style={td}>{row.x.toFixed(2)}</td>
                <td style={td}>{row.y.toFixed(2)}</td>
                <td style={td}>{row.z.toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
