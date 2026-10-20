import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';
import { useLanguage, stripLangPrefix } from '../i18n/LanguageContext';
import { DEFAULT_LANG } from '../i18n/locale';

/**
 * Site name in the navbar, right after the search box. Links back to the home
 * page of the current language. It is the page <h1> only on the home page —
 * every other page already has its own content heading.
 */
export default function AppName() {
  const { tokens } = useTheme();
  const { ut } = useLocale();
  const { lang } = useLanguage();
  const { pathname } = useLocation();
  const isHome = stripLangPrefix(pathname) === '/';
  const homePath = lang === DEFAULT_LANG ? '/' : `/${lang}/`;

  const title = (
    <Link
      to={homePath}
      style={{
        color: tokens.accent,
        textDecoration: 'none',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        display: 'block',
      }}
    >
      {ut('ui.brand.name')}
    </Link>
  );

  return (
    <>
      <style>{`
        .navbar-brand {
          margin: 0;
          min-width: 0;
          max-width: 100%;
          font-size: 17px;
          line-height: 24px;
          font-weight: bold;
        }
        @media (max-width: 600px) {
          .navbar-brand {
            font-size: 15px;
          }
        }
      `}</style>
      {isHome ? (
        <h1 className="navbar-brand">{title}</h1>
      ) : (
        <div className="navbar-brand">{title}</div>
      )}
    </>
  );
}
