import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useTheme } from '../hooks/useTheme';
import { useLights } from '../hooks/useLights';
import { useSSRData } from '../context/SSRDataContext';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';
import type { EnvironmentLight, LightItem, LightsPayload } from '../types/data';

/** Item rarity palette, matching the lootdrop and shop pages. */
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
 * Core light sources listed on the 常用 page, in this exact order. Keyed by the
 * locale-independent translation key so every language classifies identically.
 */
const COMMON_ORDER = [
  'Text_DesignData_Item_Item_Torch_1001',
  'Text_DesignData_Item_Item_Lantern_1001',
  'Text_DesignData_Item_Item_LanternShield_1001',
];

export default function LightsPage() {
  const ssrData = useSSRData<LightsPayload>('lights');
  const { data, loading } = useLights(ssrData);
  const { tokens } = useTheme();
  const { t, ut, lang, dict } = useLocale();
  const [activeTab, setActiveTab] = useState<
    'common' | 'uncommon' | 'environment'
  >('common');

  if (loading)
    return (
      <div style={{ textAlign: 'center', color: tokens.muted, marginTop: 100 }}>
        {ut('ui.common.loading')}
      </div>
    );

  const items = data?.items ?? [];
  // Items arrive sorted by name/rarity, so one pass groups each light source
  // with all of its quality variants.
  const groups: {
    name: string;
    translationKey: string;
    label: string;
    items: LightItem[];
  }[] = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.name === item.name) {
      last.items.push(item);
    } else {
      groups.push({
        name: item.name,
        translationKey: item.translation_key ?? '',
        label: t(item.translation_key, item.translation || item.name),
        items: [item],
      });
    }
  }
  const description = localizedSeoDescription(lang, dict, 'lights', {
    items: data?.count || undefined,
  });
  // Two pages: 常用 lists the core gear in a fixed order, everything else goes
  // to 不常用 while keeping the alphabetical order the data already has.
  const commonGroups = COMMON_ORDER.map((key) =>
    groups.find((group) => group.translationKey === key)
  ).filter((group): group is (typeof groups)[number] => group !== undefined);
  const uncommonGroups = groups.filter(
    (group) => !COMMON_ORDER.includes(group.translationKey)
  );
  const shownGroups = activeTab === 'common' ? commonGroups : uncommonGroups;

  // Environment props (torches, lamp stands, ...) arrive sorted by name/raw_name,
  // so one pass groups each prop family together on the 环境 tab.
  const environment = data?.environment ?? [];
  const envGroups: {
    translationKey: string;
    label: string;
    items: EnvironmentLight[];
  }[] = [];
  for (const item of environment) {
    const key = item.translation_key ?? item.name;
    const last = envGroups[envGroups.length - 1];
    if (last && last.translationKey === key) {
      last.items.push(item);
    } else {
      envGroups.push({
        translationKey: key,
        label: t(item.translation_key, item.translation || item.name),
        items: [item],
      });
    }
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `${ut('ui.lights.title')} | ${ut('ui.brand.name')}`}
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
        {ut('ui.lights.title')}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 8,
        }}
      >
        {ut('ui.lights.stat')
          .replace('{count}', String(data?.count ?? 0))
          .replace('{variants}', String(items.length))}
      </div>
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
        {activeTab === 'environment'
          ? ut('ui.lights.env_hint')
          : ut('ui.lights.hint')}
      </p>
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 8,
          marginBottom: 16,
        }}
      >
        {(
          [
            ['common', 'ui.lights.tab.common'],
            ['uncommon', 'ui.lights.tab.uncommon'],
            ['environment', 'ui.lights.tab.environment'],
          ] as const
        ).map(([key, labelKey]) => {
          const active = activeTab === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => setActiveTab(key)}
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
              {ut(labelKey)}
            </button>
          );
        })}
      </div>
      {activeTab === 'environment'
        ? envGroups.map((group) => (
            <section key={group.translationKey} style={{ marginBottom: 18 }}>
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
                  gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
                  gap: 8,
                }}
              >
                {group.items.map((item) => (
                  <EnvironmentCard key={item.raw_name} item={item} />
                ))}
              </div>
            </section>
          ))
        : shownGroups.map((group) => (
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
                  gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
                  gap: 8,
                }}
              >
                {group.items.map((item) => (
                  <LightCard key={item.raw_name} item={item} />
                ))}
              </div>
            </section>
          ))}
    </div>
  );
}

function LightCard({ item }: { item: LightItem }) {
  const { tokens } = useTheme();
  const { t, ut } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();
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

  // Light sources have no dedicated location page, so clicking feeds the name
  // to the search box instead of risking a dead link.
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
        gap: 3,
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
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, fontSize: 12 }}>
        <span style={{ color: tokens.muted }}>
          {ut('ui.lights.fuel')}{' '}
          <span style={{ color: tokens.text, fontWeight: 'bold' }}>
            {Math.round(item.fuel_seconds)}
            {ut('ui.lights.seconds')}
          </span>
        </span>
        <span style={{ color: tokens.muted }}>
          {ut('ui.lights.radius')}{' '}
          <span style={{ color: tokens.text, fontWeight: 'bold' }}>
            {Math.round(item.light_area_radius)}
          </span>
        </span>
      </div>
    </div>
  );
}

function EnvironmentCard({ item }: { item: EnvironmentLight }) {
  const { tokens } = useTheme();
  const { t, ut } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();
  const label = t(item.translation_key, item.translation || item.name);
  const fuel = Math.round(item.fuel_seconds);
  const fuelMax = Math.round(item.fuel_seconds_max);
  const fuelText =
    fuelMax > fuel
      ? `${fuel}~${fuelMax}${ut('ui.lights.seconds')}`
      : `${fuel}${ut('ui.lights.seconds')}`;

  // Environment props have no dedicated page either, so clicking searches the name.
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
        gap: 3,
        padding: '7px 10px',
        border: `1px solid ${tokens.border}`,
        borderLeft: `4px solid ${tokens.border}`,
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
            color: tokens.text,
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
        {item.only_in_swarm && (
          <span
            style={{
              color: tokens.muted,
              fontSize: 11,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {ut('ui.lights.swarm')}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, fontSize: 12 }}>
        <span style={{ color: tokens.muted }}>
          {ut('ui.lights.fuel')}{' '}
          <span style={{ color: tokens.text, fontWeight: 'bold' }}>
            {fuelText}
          </span>
        </span>
      </div>
    </div>
  );
}
