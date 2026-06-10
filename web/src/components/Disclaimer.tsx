import type { CSSProperties } from 'react';

const box: CSSProperties = {
  textAlign: 'center',
  color: '#ff6b6b',
  fontSize: 14,
  marginBottom: 20,
  padding: 8,
  background: '#3a3a3a',
  borderRadius: 5,
  maxWidth: 700,
  marginLeft: 'auto',
  marginRight: 'auto',
};

export default function Disclaimer() {
  return (
    <div style={box}>
      ⚠️ 数据有误差，以实际游戏内为准
      <span style={{ color: '#aaa', marginLeft: 15 }}>
        地图生成日期：2026-06-08
        <span style={{ fontSize: 10 }}> 地图页面设计-雪鸡Official</span>
      </span>
    </div>
  );
}
