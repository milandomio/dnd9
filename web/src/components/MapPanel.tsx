import { memo } from 'react';
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
        {dots.map((d, i) => {
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
        })}
        {children}
      </div>
    </div>
  );
}

export default memo(MapPanel);
