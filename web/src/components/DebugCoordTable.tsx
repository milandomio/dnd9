import { type CSSProperties } from "react";

export interface CoordRow {
  /** Unique row key (e.g. "monsterName-0") */
  key: string;
  /** Group display name */
  group: string;
  /** Original group machine name (for toggling) */
  groupKey?: string;
  /** Optional monster/entity name column (omit for single-entity pages) */
  monster?: { name: string; translation: string; color: string; onToggle?: () => void };
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

const th: CSSProperties = { padding: "4px 6px", borderBottom: "1px solid #555", textAlign: "center", verticalAlign: "middle" };
const td: CSSProperties = { padding: "3px 6px", borderBottom: "1px solid #555", textAlign: "center", alignContent: "center" };
const checkTd: CSSProperties = { ...td, width: 24, textAlign: "center", verticalAlign: "middle" };

const checkboxStyle: CSSProperties = { accentColor: "#00bcd4", cursor: "pointer", margin: 0 };
const labelStyle: CSSProperties = { cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4, userSelect: "none" };

/** Small checkbox in a header cell */
function HdrChk({ checked, onChange, label }: { checked: boolean; onChange: () => void; label: string }) {
  return (
    <label style={labelStyle}>
      <input type="checkbox" checked={checked} onChange={onChange} style={checkboxStyle} />
      {label}
    </label>
  );
}

interface Props {
  rows: CoordRow[];
  onToggleRow: (key: string) => void;
  onToggleGroup?: (groupKey: string) => void;
  onToggleFile?: (file: string) => void;
  onToggleMap?: (mapName: string) => void;
  onToggleLabel?: (label: string) => void;
  /** Show monster column (for multi-monster pages like lootdrops) */
  showMonster?: boolean;
}

export default function DebugCoordTable({ rows, onToggleRow, onToggleGroup, onToggleFile, onToggleMap, onToggleLabel, showMonster }: Props) {
  // Helper: whether ALL matched rows are visible (none hidden)
  const allVisible = (pred: (r: CoordRow) => boolean) => {
    const matched = rows.filter(pred);
    return matched.length > 0 && matched.every(r => !r.hidden);
  };
  // Whether ALL rows are hidden
  const allRowsHidden = rows.length > 0 && rows.every(r => r.hidden);

  function colToggle(pred: (r: CoordRow) => boolean) {
    const matched = rows.filter(pred);
    if (matched.length === 0) return;
    const hideAll = matched.some(r => !r.hidden);
    for (const r of matched) {
      if (hideAll && !r.hidden) onToggleRow(r.key);
      else if (!hideAll && r.hidden) onToggleRow(r.key);
    }
  }

  // ── Cell-level checkbox ──
  function CellChk({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
    return <input type="checkbox" checked={visible} onChange={onToggle} style={checkboxStyle} />;
  }

  return (
    <div style={{ marginTop: 12, background: "#3a3a3a", borderRadius: 5, padding: 10, overflowX: "auto" }}>
      <h3 style={{ textAlign: "center", color: "#00bcd4", fontSize: 18, margin: "0 0 10px" }}>所有坐标详情</h3>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, color: "#aaa" }}>
        <thead>
          <tr style={{ background: "#555", fontWeight: "bold" }}>
            <th style={checkTd}>
              <input type="checkbox" checked={!allRowsHidden}
                onChange={() => colToggle(() => true)}
                style={checkboxStyle} />
            </th>
            <th style={th}>
              {onToggleGroup ? (
                <HdrChk checked={allVisible(() => true)} onChange={() => colToggle(() => true)} label="分组" />
              ) : "分组"}
            </th>
            {showMonster && (
              <th style={th}>
                {onToggleLabel ? (
                  <HdrChk checked={allVisible(() => true)} onChange={() => colToggle(() => true)} label="怪物" />
                ) : "怪物"}
              </th>
            )}
            <th style={th}>
              {onToggleFile ? (
                <HdrChk checked={allVisible(() => true)} onChange={() => colToggle(() => true)} label="地图文件" />
              ) : "地图文件"}
            </th>
            <th style={th}>
              {onToggleMap ? (
                <HdrChk checked={allVisible(() => true)} onChange={() => colToggle(() => true)} label="地图" />
              ) : "地图"}
            </th>
            <th style={th}>
              {onToggleLabel ? (
                <HdrChk checked={allVisible(() => true)} onChange={() => colToggle(() => true)} label="标签" />
              ) : "标签"}
            </th>
            <th style={th}>X</th>
            <th style={th}>Y</th>
            <th style={th}>Z</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const isHidden = row.hidden;
            return (
              <tr key={row.key} style={{
                background: isHidden ? "#2a2a2a" : (idx % 2 === 0 ? "#333" : "#3a3a3a"),
                opacity: isHidden ? 0.35 : 1,
                textDecoration: isHidden ? "line-through" : "none",
              }}>
                <td style={checkTd}>
                  <input type="checkbox" checked={!isHidden} onChange={() => onToggleRow(row.key)}
                    style={checkboxStyle} />
                </td>
                {/* 分组 */}
                <td style={{ ...td, cursor: "pointer" }}
                    onClick={() => onToggleGroup?.(row.groupKey ?? row.group)}>
                  <label style={labelStyle} onClick={e => e.stopPropagation()}>
                    <CellChk
                      visible={allVisible(r => (r.groupKey ?? r.group) === (row.groupKey ?? row.group))}
                      onToggle={() => onToggleGroup?.(row.groupKey ?? row.group)}
                    />
                    {row.group}
                  </label>
                </td>
                {/* 怪物 */}
                {showMonster && row.monster && (
                  <td style={{ ...td, cursor: "pointer" }} onClick={() => row.monster?.onToggle?.()}>
                    <label style={labelStyle} onClick={e => e.stopPropagation()}>
                      <CellChk
                        visible={allVisible(r => r.monster?.name === row.monster?.name)}
                        onToggle={() => row.monster?.onToggle?.()}
                      />
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: row.monster.color, display: "inline-block", flexShrink: 0 }}></span>
                      {row.monster.translation}
                    </label>
                  </td>
                )}
                {/* 地图文件 */}
                <td style={{ ...td, cursor: "pointer" }}
                    onClick={() => onToggleFile?.(row.file)}>
                  <label style={labelStyle} onClick={e => e.stopPropagation()}>
                    <CellChk
                      visible={allVisible(r => r.file === row.file)}
                      onToggle={() => onToggleFile?.(row.file)}
                    />
                    {row.file}
                  </label>
                </td>
                {/* 地图 */}
                <td style={{ ...td, cursor: "pointer" }}
                    onClick={() => onToggleMap?.(row.mapName)}>
                  <label style={labelStyle} onClick={e => e.stopPropagation()}>
                    <CellChk
                      visible={allVisible(r => r.mapName === row.mapName)}
                      onToggle={() => onToggleMap?.(row.mapName)}
                    />
                    {row.mapLabel}
                  </label>
                </td>
                {/* 标签 */}
                <td style={{ ...td, cursor: "pointer", fontSize: 11 }}
                    onClick={() => onToggleLabel?.(row.label)}>
                  <label style={labelStyle} onClick={e => e.stopPropagation()}>
                    <CellChk
                      visible={allVisible(r => r.label === row.label)}
                      onToggle={() => onToggleLabel?.(row.label)}
                    />
                    {row.label}
                  </label>
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
