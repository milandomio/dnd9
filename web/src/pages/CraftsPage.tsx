import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useCrafts } from '../hooks/useCrafts';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';
import type { CraftRecipe, CraftsPayload } from '../types/data';

/** Item rarity palette, matching the lights, lootdrop and shop pages. */
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

export default function CraftsPage() {
  const ssrData = useSSRData<CraftsPayload>('crafts');
  const { data, loading } = useCrafts(ssrData);
  const { tokens } = useTheme();
  const { t, ut, lang, dict } = useLocale();
  const [activeTab, setActiveTab] = useState('');

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  const merchants = data?.merchants ?? [];
  const selected =
    merchants.find((merchant) => merchant.name === activeTab) ?? merchants[0];

  // Recipes arrive sorted by merchant, then item, then rarity, so one pass
  // groups each crafted item with all of its quality tiers.
  const groups: {
    name: string;
    label: string;
    recipes: CraftRecipe[];
  }[] = [];
  for (const recipe of data?.recipes ?? []) {
    if (!selected || recipe.merchant !== selected.name) continue;
    const last = groups[groups.length - 1];
    if (last && last.name === recipe.name) {
      last.recipes.push(recipe);
    } else {
      groups.push({
        name: recipe.name,
        label: t(recipe.translation_key, recipe.translation || recipe.name),
        recipes: [recipe],
      });
    }
  }

  const description = localizedSeoDescription(lang, dict, 'crafts', {
    items: data?.item_count || undefined,
  });

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${ut('ui.crafts.title')} | ${ut('ui.brand.name')}`}
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
        {ut('ui.crafts.title')}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 8,
        }}
      >
        {ut('ui.crafts.stat')
          .replace('{merchants}', String(merchants.length))
          .replace('{items}', String(data?.item_count ?? 0))
          .replace('{recipes}', String(data?.recipe_count ?? 0))}
      </div>
      <p
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 13,
          lineHeight: 1.7,
          maxWidth: 680,
          margin: '0 auto 20px',
        }}
      >
        {ut('ui.crafts.hint')}
      </p>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 8,
          marginBottom: 16,
        }}
      >
        {merchants.map((merchant) => {
          const active = selected?.name === merchant.name;
          const label =
            merchant.kind === 'ingot'
              ? ut('ui.crafts.tab.ingots')
              : t(merchant.translation_key, merchant.display || merchant.name);
          return (
            <button
              key={merchant.name}
              type="button"
              onClick={() => setActiveTab(merchant.name)}
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
              {label}
              <span
                style={{
                  color: tokens.muted,
                  fontSize: 12,
                  fontWeight: 'normal',
                  marginLeft: 6,
                }}
              >
                {merchant.item_count}
              </span>
            </button>
          );
        })}
      </div>
      {groups.map((group) => (
        <section key={group.name} style={{ marginBottom: 18 }}>
          <h2
            style={{
              fontSize: 17,
              color: tokens.text,
              borderLeft: `3px solid ${tokens.accent}`,
              paddingLeft: 8,
              marginBottom: 8,
            }}
          >
            {group.label}
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 8,
            }}
          >
            {group.recipes.map((recipe) => (
              <CraftCard key={recipe.recipe_id} recipe={recipe} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function CraftCard({ recipe }: { recipe: CraftRecipe }) {
  const { tokens } = useTheme();
  const { t, ut } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();
  const label = t(recipe.translation_key, recipe.translation || recipe.name);
  const rarityColor = recipe.rarity
    ? (RARITY_COLORS[recipe.rarity] ?? tokens.border)
    : tokens.border;
  const rarityLabel = recipe.rarity
    ? t(
        `ui.shops.rarity.${recipe.rarity.toLowerCase()}`,
        ut(`ui.shops.rarity.${recipe.rarity.toLowerCase()}`)
      )
    : '';

  // Recipes have no dedicated page, so clicking feeds the name to the search box.
  const searchForItem = () =>
    navigate(location.pathname, { state: { searchQuery: label } });

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={searchForItem}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          searchForItem();
        }
      }}
      title={ut('ui.search.search')}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        padding: '7px 10px',
        border: `1px solid ${rarityColor}`,
        borderLeft: `4px solid ${rarityColor}`,
        borderRadius: 6,
        background: tokens.surface,
        height: '100%',
        boxSizing: 'border-box',
        cursor: 'pointer',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <span
          style={{
            color: rarityColor,
            fontSize: 14,
            fontWeight: 'bold',
            minWidth: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {label}
        </span>
        {rarityLabel && (
          <span
            style={{
              color: rarityColor,
              fontSize: 11,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {rarityLabel}
          </span>
        )}
      </div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          fontSize: 12,
          color: tokens.muted,
          alignItems: 'baseline',
        }}
      >
        <span>{ut('ui.crafts.materials')}</span>
        {recipe.requirements.map((requirement) => (
          <span key={requirement.raw_name} style={{ color: tokens.muted }}>
            <span
              style={{
                color: requirement.rarity
                  ? (RARITY_COLORS[requirement.rarity] ?? tokens.text)
                  : tokens.text,
                fontWeight: 'bold',
              }}
            >
              {t(
                requirement.translation_key,
                requirement.translation || requirement.name
              )}
            </span>
            <span style={{ color: tokens.muted }}>×{requirement.amount}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
