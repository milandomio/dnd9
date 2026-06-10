import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { useTheme } from '../hooks/useTheme';

export default function Disclaimer() {
  const { tokens } = useTheme();
  const [date, setDate] = useState('');
  const box: CSSProperties = {
    textAlign: 'center',
    color: '#ff6b6b',
    fontSize: 14,
    marginBottom: 20,
    padding: 8,
    background: tokens.surface,
    borderRadius: 5,
    maxWidth: 700,
    marginLeft: 'auto',
    marginRight: 'auto',
  };

  useEffect(() => {
    fetch('./data/json/meta.json')
      .then((r) => r.json())
      .then((d) => setDate(d.dataDate || ''))
      .catch(() => {});
  }, []);

  return (
    <div style={box}>
      ⚠️ 数据有误差，以实际游戏内为准
      <span style={{ color: tokens.muted, marginLeft: 15 }}>
        地图生成日期：{date}
        <span style={{ fontSize: 10 }}> 地图页面设计-雪鸡Official</span>
      </span>
    </div>
  );
}
