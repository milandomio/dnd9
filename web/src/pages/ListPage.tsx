import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import DebugPanel from '../components/DebugPanel';
import { dataUrl } from '../utils/dataUrl';
import { getPageEntries, type SearchEntry } from '../hooks/useSearchIndex';
import { useLanguage } from '../i18n/LanguageContext';
import { useLocale } from '../i18n/useLocale';
import { ssrLocalizedTitle } from '../i18n/ssrTitle';
import { localizedSeoDescription } from '../i18n/seo';

type IndexEntry = SearchEntry & {
  category?: string;
  coordCount?: number;
  type?: string;
  // lootdrops SSR data fields
  variant_count?: number;
  translation_key?: string;
  monsters?: string[];
  monster_translations?: string[];
  monster_translation_keys?: string[];
  max_score?: number;
  hr100?: boolean;
  item_type?: string;
  item_category_key?: string;
  item_category_translation?: string;
  item_subtype_keys?: string[];
  item_subtype_translations?: string[];
};

type LootGroup = {
  key: string;
  label: string;
  icon: string;
  items: IndexEntry[];
  labelKey?: string;
  categoryKey?: string;
  categoryTranslation?: string;
  subtypeKeys?: string[];
  subtypeTranslations?: string[];
};

const NAV_KEY_LOOKUP: Record<string, string> = {
  items: 'ui.nav.items',
  monsters: 'ui.nav.monsters',
  props: 'ui.nav.props',
  lootdrops: 'ui.nav.lootdrops',
};

const LOOT_GROUP_KEYS: Record<string, string> = {
  ['神器']: 'ui.list.artifact',
  ['小型神器']: 'ui.list.mini_artifact',
  ['稀有掉落']: 'ui.list.rare_drop',
  ['物品']: 'ui.list.item',
  ['饰品']: 'ui.list.accessory',
  ['武器装备']: 'ui.list.weapon',
};

const ITEM_GROUP_SEPARATOR = '\u001f';
const ITEM_CATEGORY_ORDER = ['Utility', 'Misc', 'Accessory', 'Armor', 'Weapon'];
const ITEM_CATEGORY_ICONS: Record<string, string> = {
  Utility: '🧪',
  Misc: '📦',
  Accessory: '💍',
  Armor: '🛡️',
  Weapon: '⚔️',
};

function itemCategoryName(categoryKey: string): string {
  const marker = '_Category_';
  const index = categoryKey.lastIndexOf(marker);
  return index >= 0 ? categoryKey.slice(index + marker.length) : '';
}

function groupLootdrops(items: IndexEntry[]): LootGroup[] {
  const weapon: IndexEntry[] = [];
  const accessory: IndexEntry[] = [];
  const rare: IndexEntry[] = [];
  const artifact: IndexEntry[] = [];
  const hr100: IndexEntry[] = [];
  const misc: IndexEntry[] = [];
  const typedGroups = new Map<string, LootGroup>();
  for (const item of items) {
    if (item.name.endsWith('_8001')) {
      artifact.push(item);
      continue;
    }
    if (item.hr100) {
      hr100.push(item);
      continue;
    }
    const vc = item.variant_count ?? 1;
    const ms = item.max_score ?? 0;
    if (ms > 0 && ms < 1) {
      rare.push(item);
      continue;
    }
    if (item.item_category_key) {
      const subtypeKeys = item.item_subtype_keys ?? [];
      const key = [item.item_category_key, ...subtypeKeys].join(
        ITEM_GROUP_SEPARATOR
      );
      let group = typedGroups.get(key);
      if (!group) {
        const category = itemCategoryName(item.item_category_key);
        group = {
          key,
          label: key,
          icon: ITEM_CATEGORY_ICONS[category] ?? '📦',
          items: [],
          categoryKey: item.item_category_key,
          categoryTranslation: item.item_category_translation,
          subtypeKeys,
          subtypeTranslations: item.item_subtype_translations,
        };
        typedGroups.set(key, group);
      }
      group.items.push(item);
      continue;
    }
    if (vc === 7 || vc === 8) {
      weapon.push(item);
    } else if (vc === 5) {
      accessory.push(item);
    } else {
      misc.push(item);
    }
  }
  const groups: LootGroup[] = [];
  if (artifact.length)
    groups.push({
      key: 'artifact',
      label: '神器',
      labelKey: LOOT_GROUP_KEYS['神器'],
      icon: '🏺',
      items: artifact,
    });
  if (hr100.length)
    groups.push({
      key: 'mini-artifact',
      label: '小型神器',
      labelKey: LOOT_GROUP_KEYS['小型神器'],
      icon: '🪙',
      items: hr100,
    });
  if (rare.length)
    groups.push({
      key: 'rare-drop',
      label: '稀有掉落',
      labelKey: LOOT_GROUP_KEYS['稀有掉落'],
      icon: '✨',
      items: rare,
    });
  if (misc.length)
    groups.push({
      key: 'legacy-misc',
      label: '物品',
      labelKey: LOOT_GROUP_KEYS['物品'],
      icon: '📦',
      items: misc,
    });
  if (accessory.length)
    groups.push({
      key: 'legacy-accessory',
      label: '饰品',
      labelKey: LOOT_GROUP_KEYS['饰品'],
      icon: '💍',
      items: accessory,
    });
  if (weapon.length)
    groups.push({
      key: 'legacy-weapon',
      label: '武器装备',
      labelKey: LOOT_GROUP_KEYS['武器装备'],
      icon: '⚔️',
      items: weapon,
    });
  groups.push(
    ...[...typedGroups.values()].sort((a, b) => {
      const aCategory = itemCategoryName(a.categoryKey ?? '');
      const bCategory = itemCategoryName(b.categoryKey ?? '');
      const categoryDiff =
        ITEM_CATEGORY_ORDER.indexOf(aCategory) -
        ITEM_CATEGORY_ORDER.indexOf(bCategory);
      return categoryDiff || a.key.localeCompare(b.key);
    })
  );
  return groups;
}

function groupLootGroupsByCategory(groups: LootGroup[]): LootGroup[][] {
  const rows: LootGroup[][] = [];
  let rowKey = '';
  for (const group of groups) {
    const nextRowKey = group.categoryKey
      ? `category:${itemCategoryName(group.categoryKey)}`
      : 'special';
    if (nextRowKey !== rowKey) {
      rows.push([]);
      rowKey = nextRowKey;
    }
    rows[rows.length - 1].push(group);
  }
  return rows;
}

function formatLootGroupLabel(
  group: LootGroup,
  t: (key: string | undefined, fallback: string) => string,
  ut: (key: string) => string,
  delimiter: string
): string {
  const translatePart = (key: string, fallback: string) => {
    const value = t(key, fallback);
    return value === key ? fallback : value;
  };
  if (!group.categoryKey) {
    return ut(group.labelKey || '') || group.label;
  }
  const unknownLabel = ut('ui.list.item_group_unknown');
  const category = translatePart(
    group.categoryKey,
    group.categoryTranslation || unknownLabel
  );
  const subtype = (group.subtypeKeys ?? [])
    .map((key, index) =>
      translatePart(key, group.subtypeTranslations?.[index] || unknownLabel)
    )
    .join(delimiter);
  if (!subtype) return category;
  return ut('ui.list.item_group')
    .replace('{category}', category)
    .replace('{type}', subtype);
}

export default function ListPage() {
  const { page: paramPage } = useParams<{ page: string }>();
  const { pathname } = useLocation();
  const VALID_PAGES = ['items', 'monsters', 'props', 'lootdrops'];
  // Explicit routes like /lootdrops have no :page param; derive from pathname
  const lastSegment = pathname.split('/').filter(Boolean).pop() || '';
  const page =
    paramPage || (VALID_PAGES.includes(lastSegment) ? lastSegment : '');
  const ssrData = useSSRData<IndexEntry[]>(`list-${page}`);
  const [data, setData] = useState<IndexEntry[]>(ssrData || []);
  const [debug, setDebug] = useState(false);
  const [activeLootGroup, setActiveLootGroup] = useState<string | null>(null);
  const dataVersion = useDataVersion();
  const { tokens } = useTheme();
  const { lang, withLangPrefix } = useLanguage();
  const { t, ut, dict } = useLocale();
  const pageLabel = ut(NAV_KEY_LOOKUP[page!] || '') || page! || '';
  const locationsLabel = ut('ui.list.locations');
  const validItemCount = ut('ui.list.valid_items').replace(
    '{count}',
    String(data.length)
  );
  const delimiter = ['zh-Hans', 'zh-Hant', 'ja'].includes(lang) ? '、' : ', ';
  const description = localizedSeoDescription(lang, dict, 'list', {
    category: page,
    count: data.length || undefined,
  });
  const lootGroups = page === 'lootdrops' ? groupLootdrops(data) : [];
  const lootGroupRows = groupLootGroupsByCategory(lootGroups);
  const selectedLootGroup =
    lootGroups.find((group) => group.key === activeLootGroup) ?? lootGroups[0];

  useEffect(() => {
    if (!dataVersion) return;
    if (!page || !['items', 'monsters', 'props', 'lootdrops'].includes(page))
      return;
    if (ssrData) return;
    getPageEntries(dataVersion, page, lang).then((entries) => {
      if (entries.length > 0) {
        setData(entries as IndexEntry[]);
      } else {
        // fallback: search_index has no data for this page
        fetch(dataUrl(dataVersion, `/data/json/${page}.json`))
          .then((r) => r.json())
          .then(setData)
          .catch(console.error);
      }
    });
  }, [page, dataVersion, lang]);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          {ssrLocalizedTitle() ??
            `【${pageLabel}】${locationsLabel} | ${ut('ui.brand.name')}`}
        </title>
        <meta name="description" content={description} />
        <meta name="keywords" content={ut('ui.seo.keywords')} />
        <meta
          property="og:title"
          content={`【${pageLabel}】${locationsLabel} | ${ut('ui.brand.name')}`}
        />
        <meta property="og:description" content={description} />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 20,
        }}
      >
        【{pageLabel}】{locationsLabel}
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 20,
        }}
      >
        {validItemCount}
      </div>
      <DebugPanel
        buttons={[
          {
            label: ut('ui.common.show_all'),
            activeLabel: ut('ui.common.debug_off'),
            active: debug,
            onClick: () => setDebug(!debug),
          },
        ]}
      />
      <div
        className="section-content"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 20,
        }}
      >
        {page === 'props'
          ? // Group props by type (decoration vs props)
            (() => {
              const decorations = data.filter((e) => e.type === 'decoration');
              const propsEntities = data.filter((e) => e.type !== 'decoration');
              const groups: {
                label: string;
                icon: string;
                items: IndexEntry[];
              }[] = [];
              if (propsEntities.length > 0)
                groups.push({
                  label: ut('ui.list.prop'),
                  icon: '🏛️',
                  items: propsEntities,
                });
              if (decorations.length > 0)
                groups.push({
                  label: ut('ui.list.decoration'),
                  icon: '🔥',
                  items: decorations,
                });

              return groups.map((group) => (
                <div key={group.label} style={{ gridColumn: '1 / -1' }}>
                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 'bold',
                      color: tokens.accent,
                      marginBottom: 12,
                      paddingLeft: 4,
                    }}
                  >
                    {group.icon} {group.label}（{group.items.length}）
                  </div>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, 1fr)',
                      gap: 20,
                    }}
                  >
                    {group.items.map((entity) => (
                      <Link
                        key={entity.name}
                        to={withLangPrefix(`/props/${entity.name}/`, lang)}
                        style={{
                          textDecoration: 'none',
                          display: 'block',
                          background: tokens.surface,
                          border: `1px solid ${tokens.border}`,
                          borderRadius: 8,
                          padding: 20,
                          textAlign: 'center',
                          transition: 'transform 0.2s, box-shadow 0.2s',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-5px)';
                          e.currentTarget.style.boxShadow =
                            '0 5px 15px rgba(0,0,0,0.5)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'none';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                      >
                        <div
                          style={{
                            color: tokens.text,
                            fontSize: 18,
                            fontWeight: 'bold',
                          }}
                        >
                          {t(
                            entity.translation_key,
                            entity.translation || entity.name
                          )}
                        </div>
                        {debug && (
                          <div
                            style={{
                              color: tokens.muted,
                              fontSize: 12,
                              marginTop: 4,
                            }}
                          >
                            {t(entity.translation_key, entity.translation)}【
                            {entity.name}】
                          </div>
                        )}
                      </Link>
                    ))}
                  </div>
                </div>
              ));
            })()
          : page === 'lootdrops'
            ? (() => {
                return (
                  <>
                    <div
                      role="tablist"
                      aria-label={pageLabel}
                      style={{
                        gridColumn: '1 / -1',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 8,
                        marginBottom: 4,
                      }}
                    >
                      {lootGroupRows.map((row, rowIndex) => (
                        <div
                          key={rowIndex}
                          style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: 8,
                          }}
                        >
                          {row.map((group) => {
                            const isActive =
                              selectedLootGroup?.key === group.key;
                            const label = formatLootGroupLabel(
                              group,
                              t,
                              ut,
                              delimiter
                            );
                            return (
                              <button
                                key={group.key}
                                type="button"
                                role="tab"
                                aria-selected={isActive}
                                onClick={() => setActiveLootGroup(group.key)}
                                style={{
                                  flex: '0 1 auto',
                                  minHeight: 42,
                                  padding: '8px 12px',
                                  color: isActive ? tokens.bg : tokens.accent,
                                  background: isActive
                                    ? tokens.accent
                                    : tokens.surface,
                                  border: `1px solid ${tokens.accent}`,
                                  borderRadius: 6,
                                  cursor: 'pointer',
                                  fontSize: 15,
                                  fontWeight: 'bold',
                                  transition: 'background 0.2s, color 0.2s',
                                }}
                              >
                                {group.icon} {label} （{group.items.length}）
                              </button>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                    {selectedLootGroup && (
                      <div
                        key={selectedLootGroup.key}
                        role="tabpanel"
                        style={{
                          gridColumn: '1 / -1',
                          display: 'grid',
                          gridTemplateColumns: 'repeat(3, 1fr)',
                          gap: 20,
                        }}
                      >
                        {selectedLootGroup.items.map((entity) => {
                          const vc = entity.variant_count ?? 1;
                          const isAlreadyVariant = /_\d{4}$/.test(entity.name);
                          const target =
                            vc > 1 &&
                            !isAlreadyVariant &&
                            !entity.name.endsWith('_8001')
                              ? `${entity.name}_5001`
                              : entity.name;
                          return (
                            <Link
                              key={entity.name}
                              to={withLangPrefix(`/lootdrops/${target}/`, lang)}
                              style={{
                                textDecoration: 'none',
                                display: 'block',
                                background: tokens.surface,
                                border: `1px solid ${tokens.border}`,
                                borderRadius: 8,
                                padding: 20,
                                textAlign: 'center',
                                transition: 'transform 0.2s, box-shadow 0.2s',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.transform =
                                  'translateY(-5px)';
                                e.currentTarget.style.boxShadow =
                                  '0 5px 15px rgba(0,0,0,0.5)';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.transform = 'none';
                                e.currentTarget.style.boxShadow = 'none';
                              }}
                            >
                              <div
                                style={{
                                  color: tokens.text,
                                  fontSize: 18,
                                  fontWeight: 'bold',
                                }}
                              >
                                {t(
                                  entity.translation_key,
                                  entity.translation || entity.name
                                )}
                              </div>
                              {debug && (
                                <div
                                  style={{
                                    color: tokens.muted,
                                    fontSize: 12,
                                    marginTop: 4,
                                  }}
                                >
                                  {t(
                                    entity.translation_key,
                                    entity.translation
                                  )}
                                  【{entity.name}】
                                </div>
                              )}
                              {entity.monsters &&
                                entity.monsters.length > 0 && (
                                  <div
                                    style={{
                                      color: tokens.text,
                                      fontSize: 13,
                                      marginTop: 6,
                                      lineHeight: 1.5,
                                    }}
                                  >
                                    {ut('ui.list.target')}{' '}
                                    <span style={{ color: tokens.muted }}>
                                      {entity.monster_translations &&
                                        (entity.monster_translations.length <= 6
                                          ? entity.monster_translations
                                          : entity.monster_translations.slice(
                                              0,
                                              5
                                            )
                                        )
                                          .map((mt, i) =>
                                            t(
                                              entity.monster_translation_keys?.[
                                                i
                                              ] ?? '',
                                              mt
                                            )
                                          )
                                          .join(delimiter)}
                                      {entity.monster_translations &&
                                        entity.monster_translations.length >
                                          6 &&
                                        '...'}
                                    </span>
                                  </div>
                                )}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </>
                );
              })()
            : // Default rendering for non-props, non-lootdrops pages
              data.map((entity) => (
                <Link
                  key={entity.name}
                  to={withLangPrefix(`/${page}/${entity.name}/`, lang)}
                  style={{
                    textDecoration: 'none',
                    display: 'block',
                    background: tokens.surface,
                    border: `1px solid ${tokens.border}`,
                    borderRadius: 8,
                    padding: 20,
                    textAlign: 'center',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-5px)';
                    e.currentTarget.style.boxShadow =
                      '0 5px 15px rgba(0,0,0,0.5)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'none';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div
                    style={{
                      color: tokens.text,
                      fontSize: 18,
                      fontWeight: 'bold',
                    }}
                  >
                    {t(
                      entity.translation_key,
                      entity.translation || entity.name
                    )}
                  </div>
                  {debug && (
                    <div
                      style={{
                        color: tokens.muted,
                        fontSize: 12,
                        marginTop: 4,
                      }}
                    >
                      {t(entity.translation_key, entity.translation)}【
                      {entity.name}】
                    </div>
                  )}
                  {entity.monsters &&
                    entity.monsters.length > 0 &&
                    page === 'lootdrops' && (
                      <div
                        style={{
                          color: tokens.text,
                          fontSize: 13,
                          marginTop: 6,
                          lineHeight: 1.5,
                        }}
                      >
                        {entity.variant_count && entity.variant_count > 1 ? (
                          <>
                            {' '}
                            [
                            {ut('ui.list.variant').replace(
                              '{count}',
                              String(entity.variant_count)
                            )}
                            ] {ut('ui.list.target')}{' '}
                          </>
                        ) : (
                          <> {ut('ui.list.target')} </>
                        )}
                        <span style={{ color: tokens.muted }}>
                          {entity.monster_translations &&
                            (entity.monster_translations.length <= 6
                              ? entity.monster_translations
                              : entity.monster_translations.slice(0, 5)
                            )
                              .map((mt, i) =>
                                t(
                                  entity.monster_translation_keys?.[i] ?? '',
                                  mt
                                )
                              )
                              .join(delimiter)}
                          {entity.monster_translations &&
                            entity.monster_translations.length > 6 &&
                            '...'}
                        </span>
                      </div>
                    )}
                </Link>
              ))}
      </div>
    </div>
  );
}
