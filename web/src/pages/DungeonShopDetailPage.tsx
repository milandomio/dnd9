import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useShopDetail } from '../hooks/useDungeonShops';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';
import type { ShopDetail, ShopDifficulty, ShopItem } from '../types/data';

/** Shop slot -> the item group it sells, for a readable section heading. */
const SLOT_LABEL_KEYS: Record<number, string> = {
  1: 'ui.shops.slot.potion',
  2: 'ui.shops.slot.bandage',
  3: 'ui.shops.slot.luck',
  4: 'ui.shops.slot.cursed_water',
  5: 'ui.shops.slot.pickaxe',
  6: 'ui.shops.slot.campfire',
  7: 'ui.shops.slot.gem',
  8: 'ui.shops.slot.material',
  10: 'ui.shops.slot.key',
  11: 'ui.shops.slot.gold',
  12: 'ui.shops.slot.lantern',
};

const DIFFICULTY_LABEL_KEYS: Record<string, string> = {
  N: 'ui.shops.difficulty.normal',
  HR: 'ui.shops.difficulty.highroller',
};

export default function DungeonShopDetailPage() {
  const { region } = useParams<{ region: string }>();
  const ssrDetail = useSSRData<ShopDetail>(`dungeon_shops/${region}`);
  const { detail, loading } = useShopDetail(region ?? '', ssrDetail);
  const [activeDifficulty, setActiveDifficulty] = useState<string>('');
  const { tokens } = useTheme();
  const { t, ut, lang, dict } = useLocale();

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  if (!detail)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.not_found')}
      </div>
    );

  const difficulties = detail.difficulties ?? [];
  const selected: ShopDifficulty | undefined =
    difficulties.find((d) => d.difficulty === activeDifficulty) ??
    difficulties[0];
  const multiDifficulty = difficulties.length > 1;
  const regionName = detail.label_key
    ? t(detail.label_key, detail.display)
    : detail.display;
  const description = localizedSeoDescription(lang, dict, 'shopRegion', {
    name: regionName,
    items: detail.total_items || undefined,
  });

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${regionName} · ${ut('ui.shops.title')} | ${ut('ui.brand.name')}`}
        </title>
        <meta name="description" content={description} />
        <meta property="og:description" content={description} />
      </Helmet>
      <div style={{ textAlign: 'center', marginBottom: 8 }}>
        <Link
          to={`/${lang}/dungeon_shops`}
          style={{ color: tokens.muted, fontSize: 13 }}
        >
          ← {ut('ui.shops.title')}
        </Link>
      </div>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 32,
          marginBottom: 8,
        }}
      >
        {regionName}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 13,
          marginBottom: 20,
        }}
      >
        {t(
          detail.merchant?.translation_key,
          detail.merchant?.display ?? detail.merchant?.merchant_name ?? ''
        )}
        {' · '}
        {ut('ui.shops.total_items').replace(
          '{count}',
          String(detail.total_items)
        )}
        {detail.exclusive_count > 0 && (
          <span style={{ color: '#E91E63' }}>
            {' · '}
            {ut('ui.shops.exclusive_count').replace(
              '{count}',
              String(detail.exclusive_count)
            )}
          </span>
        )}
      </div>

      {multiDifficulty && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 8,
            marginBottom: 16,
          }}
        >
          {difficulties.map((d) => {
            const active = d.difficulty === selected?.difficulty;
            return (
              <button
                key={d.difficulty}
                type="button"
                onClick={() => setActiveDifficulty(d.difficulty)}
                style={{
                  padding: '7px 18px',
                  border: `1px solid ${active ? tokens.accent : tokens.border}`,
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: 'bold',
                  color: active ? tokens.accent : tokens.muted,
                  background: active ? tokens.surface : tokens.card,
                }}
              >
                {t(DIFFICULTY_LABEL_KEYS[d.difficulty], d.difficulty)}
              </button>
            );
          })}
        </div>
      )}

      {selected &&
        selected.slots.map((slot) => (
          <section key={slot.slot} style={{ marginBottom: 22 }}>
            <h2
              style={{
                fontSize: 16,
                color: tokens.text,
                borderLeft: `3px solid ${tokens.accent}`,
                paddingLeft: 8,
                marginBottom: 10,
              }}
            >
              {t(SLOT_LABEL_KEYS[slot.slot], ut('ui.shops.slot.other'))}
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
                gap: 8,
              }}
            >
              {slot.items.map((item) => (
                <ShopItemCard key={`${slot.slot}-${item.name}`} item={item} />
              ))}
            </div>
          </section>
        ))}
    </div>
  );
}

function ShopItemCard({ item }: { item: ShopItem }) {
  const { tokens } = useTheme();
  const { t, ut, lang } = useLocale();
  const label = t(item.translation_key, item.translation || item.name);

  return (
    <Link
      to={`/${lang}/lootdrops/${item.page}/`}
      style={{ textDecoration: 'none' }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          padding: '8px 10px',
          border: `1px solid ${item.map_exclusive ? '#E91E63' : tokens.border}`,
          borderRadius: 6,
          background: tokens.surface,
          height: '100%',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              color: tokens.text,
              fontSize: 14,
              fontWeight: 'bold',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {label}
            {item.count > 1 && (
              <span style={{ color: tokens.muted, fontWeight: 'normal' }}>
                {' '}
                ×{item.count}
              </span>
            )}
          </div>
          {item.map_exclusive && (
            <div style={{ color: '#E91E63', fontSize: 11, marginTop: 2 }}>
              {ut('ui.shops.map_exclusive')}
            </div>
          )}
        </div>
        <div
          style={{
            color: '#F39C12',
            fontSize: 14,
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
          }}
        >
          {item.price}
          <span style={{ fontSize: 11, marginLeft: 2 }}>
            {ut('ui.shops.gold')}
          </span>
        </div>
      </div>
    </Link>
  );
}
