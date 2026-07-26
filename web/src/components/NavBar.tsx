import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Input, Select, Spin } from 'antd';
import {
  BulbOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
  LoadingOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useTheme } from '../hooks/useTheme';
import { useDungeonModules } from '../hooks/useDungeonModules';
import { useSearchIndex, type SearchEntry } from '../hooks/useSearchIndex';
import {
  SUPPORTED_LANGS,
  LANG_DISPLAY_NAME,
  DEFAULT_LANG,
  type SupportedLang,
} from '../i18n/locale';
import { useLanguage, stripLangPrefix } from '../i18n/LanguageContext';
import { useLocale } from '../i18n/useLocale';
import { useSSRData } from '../context/SSRDataContext';
import { formatGroupLabel } from '../utils/formatGroupLabel';

const NAV_LABEL_KEYS: Record<string, string> = {
  items: 'ui.nav.items',
  monsters: 'ui.nav.monsters',
  props: 'ui.nav.props',
  lootdrops: 'ui.nav.lootdrops',
  explore: 'ui.nav.explore',
  quest_items: 'ui.nav.quest_items',
  quest_npc: 'ui.nav.quest_npc',
  dungeon_modules: 'ui.nav.dungeon_modules',
};

const PAGE_TAG_KEYS: Record<string, string> = {
  items: 'ui.search.tag.item',
  monsters: 'ui.search.tag.monster',
  props: 'ui.search.tag.prop',
  lootdrops: 'ui.search.tag.lootdrop',
  explore: 'ui.search.tag.explore',
  quest_npc: 'ui.search.tag.npc',
  quest_items: 'ui.search.tag.quest',
  dungeon_modules: 'ui.search.tag.module',
  _nav: 'ui.search.tag.nav',
};

const RECENT_KEY = 'recentSearches';
const MAX_RECENT = 5;

function getRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
  } catch {
    return [];
  }
}

export default function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { dark, tokens, toggle } = useTheme();
  const { lang, withLangPrefix } = useLanguage();
  const { t, ut } = useLocale();
  const { modules } = useDungeonModules();
  const isDetailTemplate = useSSRData<boolean>('__detailTemplate') === true;
  const { index: searchIndex, loading: searchLoading } = useSearchIndex();
  const contentPath = stripLangPrefix(location.pathname);
  const parts = contentPath.split('/').filter(Boolean);

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchEntry[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>(getRecent);

  // Auto-trigger search from location state (e.g. quest objective magnifier)
  useEffect(() => {
    const state = location.state as { searchQuery?: string } | null;
    if (state?.searchQuery) {
      setQuery(state.searchQuery);
      navigate(location.pathname, { replace: true, state: {} });
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      });
    }
  }, [location.state]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSelectedIdx(-1);
      return;
    }
    if (!searchIndex) return;
    const q = query.toLowerCase();
    const filtered = searchIndex
      .filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.translation.toLowerCase().includes(q)
      )
      .sort((a, b) => {
        const an = a.name.toLowerCase();
        const at = a.translation.toLowerCase();
        const bn = b.name.toLowerCase();
        const bt = b.translation.toLowerCase();
        const score = (n: string, t: string) =>
          n === q || t === q ? 0 : n.startsWith(q) || t.startsWith(q) ? 1 : 2;
        const diff = score(an, at) - score(bn, bt);
        if (diff !== 0) return diff;
        return a.page === 'lootdrops' ? -1 : b.page === 'lootdrops' ? 1 : 0;
      })
      .slice(0, 50);
    setResults(filtered);
    setShowDropdown(filtered.length > 0);
    setSelectedIdx(-1);
  }, [query, searchIndex]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const saveRecent = (term: string) => {
    if (!term.trim()) return;
    const list = getRecent().filter((t) => t !== term);
    list.unshift(term);
    if (list.length > MAX_RECENT) list.length = MAX_RECENT;
    localStorage.setItem(RECENT_KEY, JSON.stringify(list));
    setRecentSearches(list);
  };

  const handleSelect = (hit: SearchEntry) => {
    if (query.trim()) saveRecent(query.trim());
    setQuery('');
    setShowDropdown(false);
    navigate(withLangPrefix(hit.url, lang));
  };

  const handleLangChange = (nextLang: SupportedLang) => {
    window.location.href = withLangPrefix(location.pathname, nextLang);
  };

  const handleRecentClick = (term: string) => {
    setQuery(term);
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      if (selectedIdx >= 0 && results[selectedIdx]) {
        handleSelect(results[selectedIdx]);
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  };

  const linkStyle = {
    color: tokens.accent,
    textDecoration: 'none' as const,
    fontSize: 15,
    fontWeight: 'bold' as const,
    padding: '6px 16px',
    border: `1px solid ${tokens.accent}`,
    borderRadius: 5,
    cursor: 'pointer' as const,
    transition: 'all 0.2s',
  };

  const breadcrumbs: { label: string; path: string }[] = [];
  if (!isDetailTemplate && parts.length >= 2) {
    for (let i = 0; i < parts.length - 1; i++) {
      const key = parts[i];
      const uiKey = NAV_LABEL_KEYS[key];
      let label = uiKey ? ut(uiKey) : key;
      const path = `/${lang}/${parts.slice(0, i + 1).join('/')}`;

      if (i === 1 && parts[0] === 'dungeon_modules') {
        const module = [...modules.values()].find(
          (entry) => entry.group === parts[1]
        );
        label = module ? formatGroupLabel(module, t, ut) : parts[1];
      }

      breadcrumbs.push({ label, path: path + '/' });
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        maxWidth: 1200,
        margin: '0 auto 15px',
        padding: '8px 20px',
        background: tokens.surface,
        borderRadius: 5,
        flexWrap: 'wrap',
        rowGap: 8,
      }}
    >
      <div
        ref={searchRef}
        style={{ position: 'relative', flex: '0 0 360px', minWidth: 0 }}
      >
        <Input
          ref={inputRef}
          prefix={<SearchOutlined style={{ color: tokens.muted }} />}
          suffix={
            searchLoading ? (
              <Spin indicator={<LoadingOutlined spin />} size="small" />
            ) : undefined
          }
          className="navbar-search-input"
          placeholder={
            searchLoading
              ? ut('ui.common.loading')
              : ut('ui.search.placeholder')
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (query.trim() && results.length > 0) setShowDropdown(true);
            else if (!query.trim() && recentSearches.length > 0)
              setShowDropdown(true);
          }}
          onKeyDown={handleKeyDown}
          disabled={searchLoading}
          allowClear
          style={{
            background: dark ? '#333' : '#fff',
            borderColor: tokens.border,
            color: tokens.text,
            borderRadius: 6,
          }}
        />
        <style>{`
          .ant-input-affix-wrapper.navbar-search-input .ant-input::placeholder {
            color: ${dark ? '#aaa' : '#888'} !important;
          }
        `}</style>
        {showDropdown && (
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              marginTop: 4,
              background: dark ? '#2c2c2c' : '#fff',
              border: `1px solid ${tokens.border}`,
              borderRadius: 6,
              maxHeight: 400,
              overflowY: 'auto',
              zIndex: 1000,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            }}
          >
            {query.trim() ? (
              results.map((hit, i) => (
                <div
                  key={`${hit.page}::${hit.name}`}
                  onClick={() => handleSelect(hit)}
                  onMouseEnter={() => setSelectedIdx(i)}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background:
                      i === selectedIdx
                        ? dark
                          ? '#444'
                          : '#e6f4ff'
                        : 'transparent',
                    transition: 'background 0.1s',
                  }}
                >
                  <span style={{ color: tokens.text, fontSize: 14 }}>
                    {t(hit.translation_key, hit.translation || hit.name)}
                    {hit.translation && hit.translation !== hit.name && (
                      <span
                        style={{
                          color: tokens.muted,
                          marginLeft: 6,
                          fontSize: 12,
                        }}
                      >
                        ({hit.name})
                      </span>
                    )}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      padding: '1px 6px',
                      borderRadius: 3,
                      background: dark ? '#555' : '#eee',
                      color: tokens.muted,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {hit.tag || ut(PAGE_TAG_KEYS[hit.page] || '') || hit.page}
                  </span>
                </div>
              ))
            ) : recentSearches.length > 0 ? (
              <div>
                <div
                  style={{
                    padding: '6px 12px 4px',
                    fontSize: 12,
                    color: tokens.muted,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <ClockCircleOutlined />
                  {ut('ui.search.recent')}
                </div>
                {recentSearches.map((term) => (
                  <div
                    key={term}
                    onClick={() => handleRecentClick(term)}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      color: tokens.text,
                      fontSize: 14,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = dark
                        ? '#444'
                        : '#e6f4ff';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <span>{term}</span>
                    <span style={{ fontSize: 11, color: tokens.muted }}>
                      {ut('ui.search.search')}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexWrap: 'wrap',
          rowGap: 6,
        }}
      >
        <GlobalOutlined style={{ color: tokens.muted, fontSize: 16 }} />
        <Select
          size="small"
          value={lang}
          onChange={handleLangChange}
          options={SUPPORTED_LANGS.map((value) => ({
            value,
            label: LANG_DISPLAY_NAME[value],
          }))}
          style={{ width: '7em' }}
          virtual={false}
          listHeight={320}
          getPopupContainer={(triggerNode) =>
            triggerNode.parentElement || document.body
          }
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <BulbOutlined
            style={{ color: dark ? '#ffd700' : '#333', fontSize: 16 }}
          />
          <button
            onClick={toggle}
            aria-label={ut('ui.common.toggle_theme')}
            style={{
              width: 36,
              height: 20,
              borderRadius: 10,
              border: 'none',
              cursor: 'pointer',
              position: 'relative',
              background: dark ? '#555' : tokens.accent,
              transition: 'background 0.2s',
              padding: 0,
            }}
          >
            <span
              style={{
                position: 'absolute',
                top: 2,
                left: dark ? 2 : 18,
                width: 16,
                height: 16,
                borderRadius: '50%',
                background: '#fff',
                transition: 'left 0.2s',
              }}
            />
          </button>
        </div>
        {breadcrumbs.map((crumb) => (
          <Link
            key={crumb.path}
            to={withLangPrefix(crumb.path, lang)}
            style={linkStyle}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = tokens.accent;
              e.currentTarget.style.color = dark ? '#2c2c2c' : '#fff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = tokens.accent;
            }}
          >
            {crumb.label}
          </Link>
        ))}
        <Link
          to={lang === DEFAULT_LANG ? '/' : `/${lang}/`}
          style={linkStyle}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = tokens.accent;
            e.currentTarget.style.color = dark ? '#2c2c2c' : '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = tokens.accent;
          }}
        >
          {ut('ui.common.home')}
        </Link>
      </div>
    </div>
  );
}
