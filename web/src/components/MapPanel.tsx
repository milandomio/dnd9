import { memo, useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import { applyTransform, computePixel } from './MapDebug';
import { useTheme } from '../hooks/useTheme';

export interface MapDot {
  x: number;
  y: number;
  z: number;
  color: string;
  title?: string;
}

export interface MapPanelProps {
  sx: number;
  sy: number;
  dots: MapDot[];
  offX: number;
  offY: number;
  adj: ReturnType<typeof import('./MapDebug').getAdj>;
  range: number;
  /** true = 单分类，用 zColor 着色圆点；false = 多分类，用 dot.color */
  singleCategory?: boolean;
  children?: React.ReactNode;
  /** Image URL (direct or blob) managed by the parent */
  imageSrc: string;
}

function zColor(z: number): string {
  if (z > 299) return '#00ffff';
  if (z >= -299) return '#ffff00';
  return '#ff3333';
}

const GLOW = '0 0 4px #fff, 0 0 2px #000';
const DENSE_DOT_THRESHOLD = 300;

interface ProjectedDot extends MapDot {
  px: number;
  py: number;
  markerColor: string;
  textColor: string;
  redOutline: boolean;
  label: string;
}

interface DenseDotLayerProps {
  sx: number;
  sy: number;
  dots: MapDot[];
  offX: number;
  offY: number;
  adj: ReturnType<typeof import('./MapDebug').getAdj>;
  range: number;
  singleCategory?: boolean;
}

function DenseDotLayer({
  sx,
  sy,
  dots,
  offX,
  offY,
  adj,
  range,
  singleCategory,
}: DenseDotLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const projectedDots = useMemo<ProjectedDot[]>(
    () =>
      dots.map((dot) => {
        const [x, y] = applyTransform(dot.x, dot.y, offX, offY, adj);
        const [px, py] = computePixel(x, y, range, sx, sy);
        const markerColor = singleCategory ? zColor(dot.z) : dot.color;
        const textColor = zColor(dot.z);
        return {
          ...dot,
          px,
          py,
          markerColor,
          textColor: textColor === '#ff3333' ? '#ffffff' : textColor,
          redOutline: textColor === '#ff3333',
          label: String(Math.round(dot.z)),
        };
      }),
    [dots, offX, offY, adj, range, singleCategory, sx, sy]
  );
  const accessibleLabel = useMemo(
    () =>
      [
        ...new Set(
          projectedDots.flatMap((dot) => (dot.title ? [dot.title] : []))
        ),
      ].join(', '),
    [projectedDots]
  );
  const hovered =
    hoveredIndex === null ? null : (projectedDots[hoveredIndex] ?? null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    const draw = () => {
      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const scale = Math.max(1, window.devicePixelRatio || 1);
      const pixelWidth = Math.round(rect.width * scale);
      const pixelHeight = Math.round(rect.height * scale);
      if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
      if (canvas.height !== pixelHeight) canvas.height = pixelHeight;

      context.setTransform(scale, 0, 0, scale, 0, 0);
      context.clearRect(0, 0, rect.width, rect.height);
      context.textAlign = 'center';
      context.textBaseline = 'top';
      context.font = '11px Arial, sans-serif';

      for (const dot of projectedDots) {
        const x = (dot.px / 100) * rect.width;
        const y = (dot.py / 100) * rect.height;
        context.beginPath();
        context.shadowColor = dot.markerColor;
        context.shadowBlur = 6;
        context.fillStyle = dot.markerColor;
        context.arc(x, y, 5.5, 0, Math.PI * 2);
        context.fill();
        context.shadowBlur = 0;
        context.strokeStyle = '#fff';
        context.lineWidth = 1;
        context.stroke();

        const labelY = y + 10;
        if (dot.redOutline) {
          context.lineWidth = 1;
          context.strokeStyle = '#ff3333';
          context.strokeText(dot.label, x, labelY);
        }
        context.fillStyle = dot.textColor;
        context.shadowColor = '#fff';
        context.shadowBlur = 4;
        context.fillText(dot.label, x, labelY);
        context.shadowColor = '#000';
        context.shadowBlur = 2;
        context.fillText(dot.label, x, labelY);
        context.shadowBlur = 0;
        context.fillText(dot.label, x, labelY);
      }
      canvas.dataset.rendered = 'true';
    };

    draw();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', draw);
      return () => window.removeEventListener('resize', draw);
    }
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [projectedDots]);

  const handlePointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    let nextIndex: number | null = null;
    let nearestDistance = Infinity;

    for (let index = 0; index < projectedDots.length; index++) {
      const dot = projectedDots[index];
      if (!dot.title) continue;
      const x = (dot.px / 100) * rect.width;
      const y = (dot.py / 100) * rect.height;
      const dx = pointerX - x;
      const dy = pointerY - y;
      const markerDistance = dx * dx + dy * dy;
      if (markerDistance <= 36 && markerDistance < nearestDistance) {
        nearestDistance = markerDistance;
        nextIndex = index;
      }
      const labelHit =
        Math.abs(dx) <= Math.max(5, dot.label.length * 3.1) &&
        pointerY >= y + 8 &&
        pointerY <= y + 23;
      if (labelHit) {
        const labelDistance = dx * dx + (pointerY - (y + 14)) ** 2;
        if (labelDistance < nearestDistance) {
          nearestDistance = labelDistance;
          nextIndex = index;
        }
      }
    }
    setHoveredIndex((current) => (current === nextIndex ? current : nextIndex));
  };

  return (
    <>
      <canvas
        ref={canvasRef}
        aria-label={accessibleLabel || 'Map points'}
        data-map-dot-canvas=""
        data-dot-count={projectedDots.length}
        title={hovered?.title}
        role="img"
        onPointerMove={handlePointerMove}
        onPointerLeave={() => setHoveredIndex(null)}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          zIndex: 10,
        }}
      />
      {hovered?.title && (
        <div
          role="tooltip"
          style={{
            position: 'absolute',
            left: `${Math.min(Math.max(hovered.px, 0), 100)}%`,
            top: `${Math.min(Math.max(hovered.py, 0), 100)}%`,
            transform: `translate(${hovered.px > 75 ? 'calc(-100% - 8px)' : '8px'}, ${hovered.py > 75 ? 'calc(-100% - 8px)' : '8px'})`,
            padding: '3px 6px',
            borderRadius: 3,
            background: 'rgba(0, 0, 0, 0.85)',
            color: '#fff',
            fontSize: 12,
            lineHeight: 1.3,
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            zIndex: 11,
          }}
        >
          {hovered.title}
        </div>
      )}
    </>
  );
}

function MapPanel({
  sx,
  sy,
  dots,
  offX,
  offY,
  adj,
  range,
  singleCategory,
  children,
  imageSrc,
}: MapPanelProps) {
  const { tokens } = useTheme();
  const imgUrl = imageSrc;

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        paddingBottom: `${(sy / sx) * 100}%`,
        backgroundColor: tokens.bg,
        border: `1px solid ${tokens.border}`,
        borderRadius: 4,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          overflow: 'hidden',
          backgroundImage: `url(${imgUrl})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        {dots.length > DENSE_DOT_THRESHOLD ? (
          <DenseDotLayer
            sx={sx}
            sy={sy}
            dots={dots}
            offX={offX}
            offY={offY}
            adj={adj}
            range={range}
            singleCategory={singleCategory}
          />
        ) : (
          dots.map((d, i) => {
            const [x, y] = applyTransform(d.x, d.y, offX, offY, adj);
            const [px, py] = computePixel(x, y, range, sx, sy);
            const col = singleCategory ? zColor(d.z) : d.color;
            const zcol = singleCategory ? col : zColor(d.z);
            const textCol = zcol === '#ff3333' ? '#ffffff' : zcol;
            const textShadow =
              zcol === '#ff3333'
                ? '0.5px 0.5px 0 #ff3333,-0.5px -0.5px 0 #ff3333,0 0 4px #fff,0 0 2px #000'
                : GLOW;
            return (
              <div
                key={i}
                title={d.title}
                style={{
                  position: 'absolute',
                  left: `${px}%`,
                  top: `${py}%`,
                  width: 9,
                  height: 9,
                  borderRadius: '50%',
                  background: col,
                  boxShadow: `0 0 6px ${col}`,
                  border: '1px solid #fff',
                  transform: 'translate(-50%, -50%)',
                  zIndex: 10,
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '100%',
                    transform: 'translateX(-50%)',
                    fontSize: 11,
                    fontFamily: 'Arial, sans-serif',
                    color: textCol,
                    whiteSpace: 'nowrap',
                    textShadow,
                    lineHeight: 1,
                    marginTop: 1,
                  }}
                >
                  {Math.round(d.z)}
                </span>
              </div>
            );
          })
        )}
        {children}
      </div>
    </div>
  );
}

export default memo(MapPanel);
