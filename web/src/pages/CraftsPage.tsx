import { useEffect, useState } from 'react';
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useCrafts } from '../hooks/useCrafts';
import { useSearchTargetSignal } from '../hooks/useSearchTargetSignal';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';
import type {
  CraftEffect,
  CraftEffectProperty,
  CraftProperties,
  CraftProperty,
  CraftRecipe,
  CraftsPayload,
} from '../types/data';

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

/**
 * Section title. Material families read 「银粉」or「蓝宝石 + 奥术精华」, equipment
 * NPC sections read like the 【掉落表】 page (「护甲：板甲」), and an empty part
 * list marks the synthetic ore tab, whose single section is named by its label.
 */
function groupLabel(
  recipe: CraftRecipe,
  t: (key: string | undefined, fallback: string) => string,
  ut: (key: string) => string,
  delimiter: string
): string {
  if (!recipe.group_parts?.length) return ut('ui.crafts.tab.ores');
  const parts = recipe.group_parts.map((part) =>
    t(part.translation_key, part.translation || part.name)
  );
  if (recipe.group_kind === 'category') {
    const category = recipe.group_category
      ? t(
          recipe.group_category.translation_key,
          recipe.group_category.translation || recipe.group_category.name
        )
      : ut('ui.list.item_group_unknown');
    return (
      ut('ui.list.item_group_prefix').replace('{category}', category) +
      parts.join(delimiter)
    );
  }
  return parts.join(' + ');
}

export default function CraftsPage() {
  const ssrData = useSSRData<CraftsPayload>('crafts');
  const { data, loading } = useCrafts(ssrData);
  const { tokens } = useTheme();
  const { t, ut, lang, dict } = useLocale();
  // The active tab is part of the route (``/crafts/{slug}/``) so search results and
  // shared links open the right crafter directly; ``/crafts/`` falls back to the
  // first tab.
  const { merchant: merchantSlug } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  // Set after mount (not during render) so a shared ?item= link hydrates the same
  // HTML as the static build before the highlight is applied.
  const [focusItem, setFocusItem] = useState('');
  // Bumped when the navbar re-emits a hit for this very page.
  const searchSignal = useSearchTargetSignal();

  useEffect(() => {
    setFocusItem(searchParams.get('item') ?? '');
  }, [searchParams]);

  useEffect(() => {
    if (!focusItem || !data) return;
    const hit = data.recipes.find((recipe) => recipe.name === focusItem);
    const routed = data.merchants.find((m) => m.slug === merchantSlug);
    const active = routed?.name ?? data.merchants[0]?.name;
    // Legacy ``/crafts/?item=`` links carry no tab segment; send them to the route
    // of the recipe's own crafter so the card is rendered and highlighted.
    if (hit && hit.merchant !== active) {
      const target = data.merchants.find((m) => m.name === hit.merchant);
      if (target) {
        navigate(
          `/${lang}/crafts/${target.slug}/?item=${encodeURIComponent(focusItem)}`,
          { replace: true }
        );
        return;
      }
    }
    const timer = setTimeout(() => {
      document
        .querySelector(`[data-craft-item="${CSS.escape(focusItem)}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
    return () => clearTimeout(timer);
  }, [focusItem, data, merchantSlug, lang, navigate, searchSignal]);

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  const merchants = data?.merchants ?? [];
  const selected =
    merchants.find((merchant) => merchant.slug === merchantSlug) ??
    merchants[0];
  const delimiter = ['zh-Hans', 'zh-Hant', 'ja'].includes(lang) ? '、' : ', ';

  // Recipes arrive sorted by merchant, then section, then item, then rarity, so
  // one pass groups every recipe of one section under one heading.
  const groups: {
    key: string;
    label: string;
    recipes: CraftRecipe[];
  }[] = [];
  for (const recipe of data?.recipes ?? []) {
    if (!selected || recipe.merchant !== selected.name) continue;
    const last = groups[groups.length - 1];
    if (last && last.key === recipe.group) {
      last.recipes.push(recipe);
    } else {
      groups.push({
        key: recipe.group,
        label: groupLabel(recipe, t, ut, delimiter),
        recipes: [recipe],
      });
    }
  }

  const description = localizedSeoDescription(lang, dict, 'crafts', {
    items: data?.item_count || undefined,
  });

  return (
    <div style={{ maxWidth: 'var(--shell-max)' as const, margin: '0 auto' }}>
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
          .replace('{groups}', String(data?.group_count ?? 0))
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
            merchant.kind === 'npc'
              ? t(merchant.translation_key, merchant.display || merchant.name)
              : ut('ui.crafts.tab.ores');
          return (
            <Link
              key={merchant.name}
              to={`/${lang}/crafts/${merchant.slug}/`}
              aria-current={active ? 'page' : undefined}
              style={{
                padding: '7px 18px',
                border: `1px solid ${active ? tokens.accent : tokens.border}`,
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 15,
                fontWeight: 'bold',
                color: active ? tokens.accent : tokens.muted,
                background: active ? tokens.surface : tokens.card,
                textDecoration: 'none',
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
                {merchant.recipe_count}
              </span>
            </Link>
          );
        })}
      </div>
      {groups.map((group) => (
        <section key={group.key} style={{ marginBottom: 18 }}>
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
            <span
              style={{
                color: tokens.muted,
                fontSize: 13,
                fontWeight: 'normal',
                marginLeft: 6,
              }}
            >
              ({new Set(group.recipes.map((recipe) => recipe.name)).size})
            </span>
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 8,
            }}
          >
            {group.recipes.map((recipe) => (
              <CraftCard
                key={recipe.recipe_id}
                recipe={recipe}
                pools={data?.property_pools}
                focused={recipe.name === focusItem}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

/**
 * One stat range, rendered the way the game tooltip does: percentage stats
 * (``ValueRatio``) read as ``raw x ratio``, so a raw action speed of 20 shows as
 * ``2%``; everything else is a flat number (armour 19, move speed -30).
 */
function formatPropertyValue(property: CraftProperty): string {
  const scale = property.ratio ? property.ratio * 100 : 1;
  const trim = (value: number) => String(Math.round(value * 100) / 100);
  const suffix = property.ratio ? '%' : '';
  const min = trim(property.min * scale);
  const max = trim(property.max * scale);
  return min === max ? `${min}${suffix}` : `${min}~${max}${suffix}`;
}

/**
 * One effect range. Unlike a stat line there is no percentage scaling: the
 * payload already holds the numbers the game tooltip shows, so a shield reads
 * ``30`` and a duration reads ``24 秒``.
 */
function formatEffectValue(property: CraftEffectProperty): string {
  const trim = (value: number) => String(Math.round(value * 100) / 100);
  const suffix = property.seconds ? ' 秒' : '';
  const min = trim(property.min);
  const max = trim(property.max);
  return min === max ? `${min}${suffix}` : `${min}~${max}${suffix}`;
}

/**
 * Stats of a crafted item, listed under its materials. The fixed lines come from
 * the item asset; the extra enchantment slots roll from a pool shared by every
 * item of one equipment slot, which the payload ships once (``property_pools``)
 * — its entries are summarised in the hover text.
 */
function CraftPropertiesLine({
  properties,
  pools,
}: {
  properties: CraftProperties;
  pools?: Record<string, CraftProperty[]>;
}) {
  const { tokens } = useTheme();
  const { t, ut } = useLocale();
  const pool = properties.random ? pools?.[properties.random.pool] : undefined;
  const label = (property: CraftProperty) =>
    t(property.translation_key, property.translation || property.type);
  const poolHint = pool?.length
    ? `${ut('ui.crafts.random_hint')}：${pool
        .map((entry) => `${label(entry)} ${formatPropertyValue(entry)}`)
        .join(' / ')}`
    : undefined;

  return (
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
      <span>{ut('ui.crafts.properties')}</span>
      {properties.primary.map((property, index) => (
        <span key={`${property.type}-${index}`} style={{ color: tokens.text }}>
          {label(property)} {formatPropertyValue(property)}
        </span>
      ))}
      {properties.random && (
        <span style={{ color: tokens.accent }} title={poolHint}>
          {ut('ui.crafts.random_properties').replace(
            '{count}',
            String(properties.random.rolls)
          )}
        </span>
      )}
    </div>
  );
}

/**
 * Effect of a crafted consumable, listed under its materials. A Protection
 * potion reads 「最大物理护盾 30 ｜ 持续时间 24 秒」 — exactly the numbers the
 * in-game tooltip shows — while a Luck potion adds a hint that the value is
 * rolled at random.
 */
function CraftEffectLine({ effect }: { effect: CraftEffect }) {
  const { tokens } = useTheme();
  const { t, ut } = useLocale();
  const label = (property: CraftEffectProperty) =>
    t(property.translation_key, property.translation || property.type);

  return (
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
      <span>{ut('ui.crafts.effect')}</span>
      {effect.values.map((property, index) => (
        <span key={`${property.type}-${index}`} style={{ color: tokens.text }}>
          {label(property)} {formatEffectValue(property)}
        </span>
      ))}
      {effect.random && (
        <span style={{ color: tokens.accent }}>
          {ut('ui.crafts.effect_random')}
        </span>
      )}
    </div>
  );
}

function CraftCard({
  recipe,
  pools,
  focused,
}: {
  recipe: CraftRecipe;
  pools?: Record<string, CraftProperty[]>;
  focused?: boolean;
}) {
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
      data-craft-item={recipe.name}
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
        boxShadow: focused ? `0 0 0 2px ${tokens.accent}` : undefined,
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
      {recipe.properties && (
        <CraftPropertiesLine properties={recipe.properties} pools={pools} />
      )}
      {recipe.effect && <CraftEffectLine effect={recipe.effect} />}
    </div>
  );
}
