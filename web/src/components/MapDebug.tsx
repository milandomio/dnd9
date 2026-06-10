import type { CSSProperties } from 'react';

export const ctrlBtn: CSSProperties = {
  background: '#555',
  color: '#ccc',
  border: '1px solid #777',
  borderRadius: 3,
  padding: '1px 6px',
  cursor: 'pointer',
  fontSize: 11,
};

export const ctrlInput: CSSProperties = {
  width: 55,
  background: '#333',
  color: '#fff',
  border: '1px solid #666',
  borderRadius: 3,
  padding: '1px 4px',
  fontSize: 11,
  textAlign: 'center',
};

export interface AdjOffsets {
  x?: number;
  y?: number;
  range?: number;
  rotate?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}

export type AdjState = Record<string, AdjOffsets>;

export function getAdj(
  mapName: string,
  modRotate: number | undefined,
  adjOffsets: AdjState
) {
  const a = adjOffsets[mapName];
  return {
    x: a?.x ?? 0,
    y: a?.y ?? 0,
    range: a?.range ?? 0,
    rotate: a?.rotate ?? modRotate ?? 1,
    mirrorX: a?.mirrorX ?? false,
    mirrorY: a?.mirrorY ?? false,
  };
}

export function applyTransform(
  ox: number,
  oy: number,
  offX: number,
  offY: number,
  adj: ReturnType<typeof getAdj>
): [number, number] {
  let x = ox;
  let y = oy;
  const r = adj.rotate;
  if (r === 1) {
    const nx = y;
    const ny = -x;
    x = nx;
    y = ny;
  } else if (r === 2) {
    x = -x;
    y = -y;
  } else if (r === 3) {
    const nx = -y;
    const ny = x;
    x = nx;
    y = ny;
  }
  if (adj.mirrorX) x = -x;
  if (adj.mirrorY) y = -y;
  x += offX;
  y += offY;
  return [x, y];
}

export function computePixel(
  x: number,
  y: number,
  range: number,
  sx: number,
  sy: number
): [number, number] {
  const multX = sx === 1 && sy === 2 ? 100 : 50;
  const centerX = sx === 1 && sy === 2 ? 100 : 50;
  const multY = 50;
  const centerY = 50;
  return [
    centerX + (x / (range || 1600)) * multX,
    centerY + (y / (range || 1600)) * multY,
  ];
}
