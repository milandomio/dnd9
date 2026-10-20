import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useShopIndex } from '../hooks/useDungeonShops';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';
import type { ShopIndex } from '../types/data';

/** Region accent + icon, keyed by the merchant variant region code. */
const REGION_THEMES: Record<string, { border: string; icon: string }> = {
  Crypts: { border: '#E91E63', icon: '💀' },
  Goblin: { border: '#4CAF50', icon: '🍄' },
  IceCavern: { border: '#00BCD4', icon: '❄️' },
};

export default function DungeonShopsPage() {
  const ssrIndex = useSSRData<ShopIndex>('dungeon_shops');
  const { index, loading } = useShopIndex(ssrIndex);
  const { tokens } = useTheme();
  const { t, ut, lang, dict } = useLocale();

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  const regions = index?.regions ?? [];
  const merchant = index?.merchants?.[0];
  const description = localizedSeoDescription(lang, dict, 'shops', {
    regions: regions.length || undefined,
  });
  return (
    <div style={{ maxWidth: 'var(--shell-max)' as const, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${ut('ui.shops.title')} | ${ut('ui.brand.name')}`}
        </title>
        <meta name="description" content={description} />
        <meta name="keywords" content={ut('ui.seo.keywords')} />
        <meta property="og:description" content={description} />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 10,
        }}
      >
        {ut('ui.shops.title')}
      </h1>
      {merchant && (
        <div
          style={{
            textAlign: 'center',
            fontSize: 15,
            color: tokens.text,
            marginBottom: 6,
          }}
        >
          {t(
            merchant.translation_key,
            merchant.display || merchant.merchant_name
          )}
        </div>
      )}
      {(() => {
        const greeting = merchant
          ? t(merchant.greeting_key, merchant.greeting || '')
          : '';
        if (!greeting) return null;
        return (
          <div
            style={{
              maxWidth: 720,
              margin: '0 auto 24px',
              textAlign: 'center',
              color: tokens.muted,
              fontSize: 13,
              lineHeight: 1.6,
              fontStyle: 'italic',
            }}
          >
            「{greeting}」
          </div>
        );
      })()}
      <div
        style={{
          display: 'grid',
          // 3 across on desktop, collapsing to 1 on narrow phones instead of
          // squeezing three fixed columns into ~110px each.
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
          maxWidth: 900,
          margin: '0 auto',
        }}
      >
        {regions.map((r) => {
          const theme = REGION_THEMES[r.region] || {
            border: '#888',
            icon: '🏪',
          };
          return (
            <Link
              key={r.region}
              to={`/${lang}/dungeon_shops/${r.region}`}
              style={{ textDecoration: 'none' }}
            >
              <div
                style={{
                  background: `linear-gradient(145deg, ${tokens.surface}, ${tokens.card})`,
                  border: `2px solid ${theme.border}`,
                  borderRadius: 12,
                  textAlign: 'center',
                  padding: '20px 16px',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: 36, marginBottom: 8 }}>
                  {theme.icon}
                </div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 'bold',
                    color: tokens.text,
                    marginBottom: 8,
                  }}
                >
                  {r.label_key ? t(r.label_key, r.display) : r.display}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: tokens.muted,
                    lineHeight: 1.6,
                  }}
                >
                  {ut('ui.shops.item_count').replace(
                    '{count}',
                    String(r.item_count)
                  )}
                  {r.exclusive_count > 0 && (
                    <div style={{ color: theme.border, marginTop: 4 }}>
                      {ut('ui.shops.exclusive_count').replace(
                        '{count}',
                        String(r.exclusive_count)
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
