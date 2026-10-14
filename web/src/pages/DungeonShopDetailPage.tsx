import { useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
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

/** Slot that sells the 4 gem attributes across 3 quality tiers. */
const GEM_SLOT = 7;

const DIFFICULTY_LABEL_KEYS: Record<string, string> = {
  N: 'ui.shops.difficulty.normal',
  HR: 'ui.shops.difficulty.highroller',
};

/** Item rarity palette, matching the lootdrop and monster-drop pages. */
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

/**
 * Render a drop chance with two significant figures throughout, so the column
 * reads consistently (99%, 27%, 7.2%, 1.3%, 0.44%) and a rare 0.435% does not
 * collapse to "0.4%".
 */
function formatChance(chance: number): string {
  const pct = chance * 100;
  if (!Number.isFinite(pct)) return '';
  if (pct === 0) return '0%';
  return `${Number(pct.toPrecision(2))}%`;
}

export default function DungeonShopDetailPage() {
  const { region } = useParams<{ region: string }>();
  const ssrDetail = useSSRData<ShopDetail>(`dungeon_shops/${region}`);
  const { detail, loading } = useShopDetail(region ?? '', ssrDetail);
  const [activeDifficulty, setActiveDifficulty] = useState<string>('');
  const { tokens } = useTheme();
  const { t, ut, lang, dict } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();

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
  // Default to High Roller: it is the richer stock players plan around, and the
  // N/HR tabs make switching trivial.
  const defaultDifficulty =
    difficulties.find((d) => d.difficulty === 'HR') ?? difficulties[0];
  const selected: ShopDifficulty | undefined =
    difficulties.find((d) => d.difficulty === activeDifficulty) ??
    defaultDifficulty;
  const multiDifficulty = difficulties.length > 1;
  const regionName = detail.label_key
    ? t(detail.label_key, detail.display)
    : detail.display;
  const merchantName = t(
    detail.merchant?.translation_key,
    detail.merchant?.display ?? detail.merchant?.merchant_name ?? ''
  );
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
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 34,
          marginBottom: 8,
        }}
      >
        {regionName}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 20,
        }}
      >
        {merchantName && (
          <>
            <button
              type="button"
              onClick={() =>
                navigate(location.pathname, {
                  state: { searchQuery: merchantName },
                })
              }
              title={ut('ui.search.search')}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                font: 'inherit',
                color: tokens.accent,
                cursor: 'pointer',
                textDecoration: 'underline dotted',
                textUnderlineOffset: 3,
              }}
            >
              {merchantName}
            </button>
            {' · '}
          </>
        )}
        {ut('ui.shops.total_items').replace(
          '{count}',
          String(selected?.item_count ?? detail.total_items)
        )}
        {(() => {
          const exclusive = selected?.exclusive_count ?? detail.exclusive_count;
          if (!exclusive) return null;
          return (
            <span style={{ color: '#E91E63' }}>
              {' · '}
              {ut('ui.shops.exclusive_count').replace(
                '{count}',
                String(exclusive)
              )}
            </span>
          );
        })()}
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
                  fontSize: 15,
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

      <p
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 13,
          lineHeight: 1.7,
          maxWidth: 640,
          margin: '0 auto 20px',
        }}
      >
        {ut('ui.shops.chance_hint')}
      </p>

      {selected &&
        selected.slots.map((slot) => (
          <section key={slot.slot} style={{ marginBottom: 22 }}>
            <h2
              style={{
                fontSize: 17,
                color: tokens.text,
                borderLeft: `3px solid ${tokens.accent}`,
                paddingLeft: 8,
                marginBottom: 8,
              }}
            >
              {t(SLOT_LABEL_KEYS[slot.slot], ut('ui.shops.slot.other'))}
            </h2>
            <div
              style={{
                display: 'grid',
                // The gem slot holds 4 attributes x 3 qualities; a 4-wide grid
                // shows that structure instead of wrapping mid-group.
                gridTemplateColumns:
                  slot.slot === GEM_SLOT
                    ? 'repeat(auto-fit, minmax(170px, 1fr))'
                    : 'repeat(auto-fill, minmax(230px, 1fr))',
                gap: 8,
              }}
            >
              {slot.items.map((item) => (
                <ShopItemCard
                  key={`${slot.slot}-${item.name}`}
                  item={item}
                  // A one-item slot is guaranteed, so "100% chance" is noise.
                  showChance={slot.items.length > 1}
                />
              ))}
            </div>
          </section>
        ))}
    </div>
  );
}

function ShopItemCard({
  item,
  showChance,
}: {
  item: ShopItem;
  showChance: boolean;
}) {
  const { tokens } = useTheme();
  const { t, ut, lang } = useLocale();
  const label = t(item.translation_key, item.translation || item.name);
  const rarityColor = item.rarity
    ? (RARITY_COLORS[item.rarity] ?? tokens.border)
    : tokens.border;
  const rarityLabel = item.rarity
    ? t(
        `ui.shops.rarity.${item.rarity.toLowerCase()}`,
        ut(`ui.shops.rarity.${item.rarity.toLowerCase()}`)
      )
    : '';

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
          gap: 10,
          padding: '10px 12px',
          // Rarity drives the border; region exclusives add a magenta accent bar.
          border: `1px solid ${rarityColor}`,
          borderLeft: item.map_exclusive
            ? `4px solid #E91E63`
            : `4px solid ${rarityColor}`,
          borderRadius: 6,
          background: tokens.surface,
          height: '100%',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              color: rarityColor,
              fontSize: 15,
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
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 6,
              alignItems: 'center',
              marginTop: 4,
              fontSize: 12,
            }}
          >
            {rarityLabel && (
              <span style={{ color: rarityColor }}>{rarityLabel}</span>
            )}
            {showChance && (
              <span style={{ color: tokens.muted }}>
                {ut('ui.shops.chance').replace(
                  '{chance}',
                  formatChance(item.chance)
                )}
              </span>
            )}
            {item.map_exclusive && (
              <span style={{ color: '#E91E63' }}>
                {ut('ui.shops.map_exclusive')}
              </span>
            )}
          </div>
        </div>
        <div
          style={{
            color: '#F39C12',
            fontSize: 15,
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
          }}
        >
          {item.price}
          <span style={{ fontSize: 12, marginLeft: 2 }}>
            {ut('ui.shops.gold')}
          </span>
        </div>
      </div>
    </Link>
  );
}
