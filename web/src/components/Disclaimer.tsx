import type { CSSProperties } from 'react';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';

export default function Disclaimer() {
  const { tokens } = useTheme();
  const date = useDataVersion();
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
    ? (() => {
        const d = new Date(Number(date) * 1000);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      })()
    : '';

  return (
    <div style={box}>
      ⚠️ 数据有误差，以实际游戏内为准
      <span style={{ color: tokens.muted, marginLeft: 15 }}>
        地图生成日期：{formattedDate}
        <span
          style={{ fontSize: 10, cursor: 'pointer' }}
          onClick={() =>
            window.open('https://www.bilibili.com/video/BV1hoR7BzExq', '_blank')
          }
        >
          {' '}
          地图页面设计-雪鸡Official
        </span>
      </span>
    </div>
  );
}
