import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useParams, Link } from 'react-router-dom';
import { useSSRData } from '../context/SSRDataContext';
import { useDataVersion } from '../hooks/useDataVersion';
import { useTheme } from '../hooks/useTheme';
import { getPageEntries, type SearchEntry } from '../hooks/useSearchIndex';

type IndexEntry = SearchEntry & {
  category?: string;
  coordCount?: number;
  type?: string;
  // lootdrops SSR data fields
  variant_count?: number;
  monsters?: string[];
  monster_translations?: string[];
  max_score?: number;
};

type LootGroup = {
  label: string;
  icon: string;
  items: IndexEntry[];
};

const LABEL_MAP: Record<string, string> = {
  items: '物品表',
  monsters: '怪物表',
  props: '实体表',
  lootdrops: '掉落表',
};

function groupLootdrops(items: IndexEntry[]): LootGroup[] {
  const weapon: IndexEntry[] = [];
  const accessory: IndexEntry[] = [];
  const rare: IndexEntry[] = [];
  const artifact: IndexEntry[] = [];
  const misc: IndexEntry[] = [];
  for (const item of items) {
    if (item.name.endsWith('_8001')) {
      artifact.push(item);
      continue;
    }
    const vc = item.variant_count ?? 1;
    if (vc === 7 || vc === 8) {
      weapon.push(item);
    } else if (vc === 5) {
      accessory.push(item);
    } else if ((item.max_score ?? 0) < 2.5) {
      rare.push(item);
    } else {
      misc.push(item);
    }
  }
  const groups: LootGroup[] = [];
  if (artifact.length)
    groups.push({ label: '神器', icon: '🏺', items: artifact });
  if (rare.length) groups.push({ label: '稀有掉落', icon: '✨', items: rare });
  if (misc.length) groups.push({ label: '物品', icon: '📦', items: misc });
  if (accessory.length)
    groups.push({ label: '饰品', icon: '💍', items: accessory });
  if (weapon.length)
    groups.push({ label: '武器装备', icon: '⚔️', items: weapon });
  return groups;
}

export default function ListPage() {
  const { page } = useParams<{ page: string }>();
  const ssrData = useSSRData<IndexEntry[]>(`list-${page}`);
  const [data, setData] = useState<IndexEntry[]>(ssrData || []);
  const [debug, setDebug] = useState(false);
  const dataVersion = useDataVersion();
  const { tokens } = useTheme();

  useEffect(() => {
    if (!page || !['items', 'monsters', 'props', 'lootdrops'].includes(page))
      return;
    if (ssrData) return;
    getPageEntries(dataVersion, page).then((entries) => {
      if (entries.length > 0) {
        setData(entries as IndexEntry[]);
      } else {
        // fallback: search_index has no data for this page
        fetch(`/data/json/${page}.json`)
          .then((r) => r.json())
          .then(setData)
          .catch(console.error);
      }
    });
  }, [page, dataVersion]);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Helmet>
        <title>
          【{LABEL_MAP[page!] ?? page}】实体位置汇总 | 越来越黑暗闪电指南
          DarkFlashNav
        </title>
        <meta
          name="description"
          content={`${LABEL_MAP[page!] ?? page} 共 ${data.length} 个实体，查询地图位置分布。`}
        />
        <meta
          name="keywords"
          content="物品查询,怪物查询,装备查询,武器查询,防具查询,饰品查询,掉落查询,游戏攻略"
        />
        <meta
          property="og:title"
          content={`【${LABEL_MAP[page!] ?? page}】实体位置汇总`}
        />
        <meta property="og:description" content={`共 ${data.length} 个实体`} />
      </Helmet>
      <h1
        style={{
          textAlign: 'center',
          color: tokens.accent,
          fontSize: 36,
          marginBottom: 20,
        }}
      >
        【{LABEL_MAP[page!] ?? page}】实体位置汇总
      </h1>
      <div
        style={{
          textAlign: 'center',
          color: tokens.muted,
          fontSize: 14,
          marginBottom: 20,
        }}
      >
        有效实体{data.length}个
      </div>
      {debug && (
        <button
          onClick={() => setDebug(false)}
          style={{
            position: 'fixed',
            top: 20,
            right: 20,
            padding: '10px 20px',
            background: '#4CAF50',
            color: '#fff',
            border: '2px solid #388E3C',
            borderRadius: 8,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 'bold',
            zIndex: 9999,
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          退出调试
        </button>
      )}
      {!debug && (
        <button
          onClick={() => setDebug(true)}
          style={{
            position: 'fixed',
            top: 20,
            right: 20,
            padding: '10px 20px',
            background: '#FFC107',
            color: '#000',
            border: '2px solid #FF9800',
            borderRadius: 8,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 'bold',
            zIndex: 9999,
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          显示全部
        </button>
      )}
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
                  label: '实体',
                  icon: '🏛️',
                  items: propsEntities,
                });
              if (decorations.length > 0)
                groups.push({ label: '装饰', icon: '🔥', items: decorations });

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
                        to={`/props/${entity.name}/`}
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
                          {entity.translation || entity.name}
                        </div>
                        {debug && (
                          <div
                            style={{
                              color: tokens.muted,
                              fontSize: 12,
                              marginTop: 4,
                            }}
                          >
                            {entity.translation}【{entity.name}】
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
                const groups = groupLootdrops(data);
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
                      {group.items.map((entity) => {
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
                            to={`/lootdrops/${target}/`}
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
                              {entity.translation || entity.name}
                            </div>
                            {debug && (
                              <div
                                style={{
                                  color: tokens.muted,
                                  fontSize: 12,
                                  marginTop: 4,
                                }}
                              >
                                {entity.translation}【{entity.name}】
                              </div>
                            )}
                            {entity.monsters && entity.monsters.length > 0 && (
                              <div
                                style={{
                                  color: tokens.text,
                                  fontSize: 13,
                                  marginTop: 6,
                                  lineHeight: 1.5,
                                }}
                              >
                                <> -目标- </>
                                <span style={{ color: tokens.muted }}>
                                  {entity.monster_translations &&
                                  entity.monster_translations.length <= 6
                                    ? entity.monster_translations.join('、')
                                    : entity.monster_translations
                                        ?.slice(0, 5)
                                        .join('、') + '...'}
                                </span>
                              </div>
                            )}
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                ));
              })()
            : // Default rendering for non-props, non-lootdrops pages
              data.map((entity) => (
                <Link
                  key={entity.name}
                  to={`/${page}/${entity.name}/`}
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
                    {entity.translation || entity.name}
                  </div>
                  {debug && (
                    <div
                      style={{
                        color: tokens.muted,
                        fontSize: 12,
                        marginTop: 4,
                      }}
                    >
                      {entity.translation}【{entity.name}】
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
                          <> [{entity.variant_count}变体] -目标- </>
                        ) : (
                          <> -目标- </>
                        )}
                        <span style={{ color: tokens.muted }}>
                          {entity.monster_translations &&
                          entity.monster_translations.length <= 6
                            ? entity.monster_translations.join('、')
                            : entity.monster_translations
                                ?.slice(0, 5)
                                .join('、') + '...'}
                        </span>
                      </div>
                    )}
                </Link>
              ))}
      </div>
    </div>
  );
}
