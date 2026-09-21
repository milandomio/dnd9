import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { useLanguage } from '../i18n/LanguageContext';
import { useLocale } from '../i18n/useLocale';
import type { MonsterLootItem, MonsterLootPool } from '../types/data';

const RARITY_COLORS: Record<string, string> = {
  Poor: '#9E9E9E',
  Common: '#BDBDBD',
  Uncommon: '#2ECC71',
  Rare: '#3498DB',
  Epic: '#9B59B6',
  Legend: '#F39C12',
  Unique: '#FFD700',
  Artifact: '#FF4500',
};

const SUFFIX_RARITY: Record<string, string> = {
  '1001': 'Poor',
  '2001': 'Common',
  '3001': 'Uncommon',
  '4001': 'Rare',
  '5001': 'Epic',
  '6001': 'Legend',
  '7001': 'Unique',
  '8001': 'Artifact',
};

const LUCK_RARITY: Record<number, string> = {
  1: 'Poor',
  2: 'Common',
  3: 'Uncommon',
  4: 'Rare',
  5: 'Epic',
  6: 'Legend',
  7: 'Unique',
  8: 'Artifact',
};

function rarityColor(item: MonsterLootItem, fallback: string): string {
  const fromSuffix = item.suffix ? SUFFIX_RARITY[item.suffix] : undefined;
  const fromLuck = LUCK_RARITY[item.luck_grade] ?? undefined;
  const rarity = fromSuffix ?? fromLuck;
  return rarity ? (RARITY_COLORS[rarity] ?? fallback) : fallback;
}

function isEventCurrencyPool(pool: MonsterLootPool): boolean {
  const raw = pool.lootdrop_id || pool.id;
  return /EventCurrency/i.test(raw);
}

function poolLabel(pool: MonsterLootPool, ut: (key: string) => string): string {
  if (pool.kind === 'quest') return ut('ui.monster_drops.quest');
  if (pool.kind === 'artifact') return ut('ui.monster_drops.artifact');
  if (pool.kind === 'consumable') return ut('ui.monster_drops.consumable');
  const raw = pool.lootdrop_id || pool.id;
  const stem = raw.replace(/^Id_Lootdrop_/i, '').replace(/^ID_Lootdrop_/i, '');
  const mapped = ut(`ui.monster_drops.pool.${stem}`);
  if (mapped !== `ui.monster_drops.pool.${stem}`) return mapped;
  return stem.replace(/^(Drop_|Spawn_)/, '');
}

interface MonsterDropSwitchProps {
  pools: MonsterLootPool[];
}

export default function MonsterDropSwitch({ pools }: MonsterDropSwitchProps) {
  const { tokens } = useTheme();
  const { lang } = useLanguage();
  const { t, ut } = useLocale();
  const visiblePools = useMemo(
    () =>
      pools.filter(
        (pool) => pool.items.length > 0 && !isEventCurrencyPool(pool)
      ),
    [pools]
  );
  const [activeId, setActiveId] = useState(() => visiblePools[0]?.id ?? '');
  if (visiblePools.length === 0) return null;
  const selected =
    visiblePools.find((pool) => pool.id === activeId) ?? visiblePools[0];

  const multi = visiblePools.length > 1;

  return (
    <div style={{ margin: '15px 0' }}>
      {multi && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
            gap: 4,
            marginBottom: -1,
            position: 'relative',
            zIndex: 1,
          }}
        >
          {visiblePools.map((pool) => {
            const isActive = pool.id === selected.id;
            return (
              <button
                key={pool.id}
                type="button"
                onClick={() => setActiveId(pool.id)}
                style={{
                  padding: '7px 14px',
                  border: `1px solid ${tokens.border}`,
                  borderBottom: isActive
                    ? 'none'
                    : `1px solid ${tokens.border}`,
                  borderRadius: '6px 6px 0 0',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 'bold',
                  color: isActive ? tokens.text : tokens.muted,
                  background: isActive ? tokens.surface : tokens.card,
                }}
              >
                {poolLabel(pool, ut)}
              </button>
            );
          })}
        </div>
      )}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          justifyContent: 'center',
          padding: 10,
          background: tokens.surface,
          border: `1px solid ${tokens.border}`,
          borderRadius: multi ? '0 5px 5px 5px' : 5,
        }}
      >
        {selected.items.map((item) => {
          const color = rarityColor(item, tokens.muted);
          const label = t(item.translation_key, item.translation || item.page);
          return (
            <Link
              key={`${item.page}-${item.suffix ?? 'base'}`}
              to={`/${lang}/lootdrops/${item.page}/`}
              style={{
                padding: '8px 15px',
                border: `2px solid ${color}`,
                borderRadius: 5,
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 'bold',
                color: tokens.text,
                background: 'transparent',
                textDecoration: 'none',
                display: 'inline-block',
              }}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
