import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';

const RARITY_COLORS: Record<string, string> = {
  粗糙: '#9E9E9E',
  普通: '#BDBDBD',
  优秀: '#2ECC71',
  罕见: '#3498DB',
  史诗: '#9B59B6',
  传奇: '#F39C12',
  独特: '#FFD700',
};

interface VariantSwitchProps {
  variantRarity: Record<string, string>;
  itemName: string;
  currentSuffix: string | null;
}

export default function VariantSwitch({
  variantRarity,
  itemName,
  currentSuffix,
}: VariantSwitchProps) {
  const { tokens } = useTheme();
  const suffixes = Object.keys(variantRarity);
  if (suffixes.length <= 1) return null;
  const defaultSuffix = suffixes.includes('5001') ? '5001' : suffixes[0];

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
        const rarity = variantRarity[suffix] ?? suffix;
        const color = RARITY_COLORS[rarity] ?? tokens.muted;
        const isActive =
          currentSuffix === suffix ||
          (!currentSuffix && suffix === defaultSuffix);
        return (
          <Link
            key={suffix}
            to={`/lootdrops/${itemName}_${suffix}/`}
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
            {rarity}
          </Link>
        );
      })}
    </div>
  );
}
