import { useTheme } from '../hooks/useTheme';

export default function HomePageTitle() {
  const { tokens } = useTheme();
  return (
    <h1
      style={{
        textAlign: 'center',
        color: tokens.accent,
        fontSize: 26,
        marginBottom: 4,
      }}
    >
      DarkFlashNav
    </h1>
  );
}
