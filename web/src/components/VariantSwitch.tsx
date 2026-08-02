import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { useLanguage } from '../i18n/LanguageContext';
import { useLocale } from '../i18n/useLocale';
import { defaultVariantSuffix } from '../utils/variant';

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

function getRarityColor(
  vr: { name: string; translation_key: string } | undefined,
  fallback: string
): string {
  if (!vr) return fallback;
  const rn = vr.translation_key.split('_').pop() || '';
  return RARITY_COLORS[rn] ?? fallback;
}

interface VariantSwitchProps {
  variantRarity: Record<string, { name: string; translation_key: string }>;
  itemName: string;
  currentSuffix: string | null;
}

export default function VariantSwitch({
  variantRarity,
  itemName,
  currentSuffix,
}: VariantSwitchProps) {
  const { tokens } = useTheme();
  const { lang } = useLanguage();
  const { t } = useLocale();
  const suffixes = Object.keys(variantRarity);
  if (suffixes.length <= 1) return null;
  const defaultSuffix = defaultVariantSuffix(suffixes);

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        justifyContent: 'center',
        margin: '15px 0',
        padding: 10,
        background: tokens.surface,
        borderRadius: 5,
      }}
    >
      {suffixes.map((suffix) => {
        const vr = variantRarity[suffix];
        const label = vr ? t(vr.translation_key, vr.name) : suffix;
        const color = getRarityColor(vr, tokens.muted);
        const isActive =
          currentSuffix === suffix ||
          (!currentSuffix && suffix === defaultSuffix);
        return (
          <Link
            key={suffix}
            to={`/${lang}/lootdrops/${itemName}_${suffix}/`}
            style={{
              padding: '8px 15px',
              border: `2px solid ${color}`,
              borderRadius: 5,
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 'bold',
              color: isActive ? '#000' : tokens.text,
              background: isActive ? color : 'transparent',
              opacity: isActive ? 1 : 0.5,
              transition: 'all 0.2s',
              textDecoration: 'none',
              display: 'inline-block',
            }}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}
