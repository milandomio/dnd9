interface LocationStatsProps {
  count: number;
  mapTranslations: string[];
}

export default function LocationStats({
  count,
  mapTranslations,
}: LocationStatsProps) {
  return (
    <>
      <strong>位置统计：共 {count} 个位置点</strong>
      <br />
      <strong>包含地图：</strong>
      {mapTranslations.join('、')}
    </>
  );
}
