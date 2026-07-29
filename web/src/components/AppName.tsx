import { useTheme } from '../hooks/useTheme';
import { useLocale } from '../i18n/useLocale';

export default function AppName() {
  const { tokens } = useTheme();
  const { ut } = useLocale();
  return (
    <h1
      style={{
        textAlign: 'center',
        color: tokens.accent,
        fontSize: 26,
        marginBottom: 4,
      }}
    >
      {ut('ui.brand.name')}
    </h1>
  );
}
