import { useTheme } from '../hooks/useTheme';

export default function AppName() {
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
      越来越黑暗闪电指南
      <div style={{ fontSize: 14, color: tokens.muted, marginTop: 4 }}>
        DarkFlashNav
      </div>
    </h1>
  );
}
