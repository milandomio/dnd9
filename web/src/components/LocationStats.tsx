import { useLocale } from '../i18n/useLocale';
import type { DungeonModule } from '../types/data';

interface LocationStatsProps {
  count: number;
  mapKeys: string[];
  modules: Map<string, DungeonModule>;
}

export default function LocationStats({
  count,
  mapKeys,
  modules,
}: LocationStatsProps) {
  const { t, ut } = useLocale();
  const sep = ut('ui.location.map_sep');
  const names = mapKeys.map((k) => {
    const mod = modules.get(k);
    return t(mod?.translation_key, mod?.translation || k);
  });

  return (
    <>
      <strong>
        {ut('ui.location.pos_stat').replace('{count}', String(count))}
      </strong>
      <br />
      <strong>{ut('ui.location.map_includes')}</strong>
      {names.join(sep)}
    </>
  );
}
