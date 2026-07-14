interface DebugButton {
  label: string;
  activeLabel: string;
  active: boolean;
  onClick: () => void;
}

interface DebugPanelProps {
  buttons: DebugButton[];
}

export default function DebugPanel({ buttons }: DebugPanelProps) {
  if (buttons.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 90,
        right: 20,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      {buttons.map((btn, i) => (
        <button
          key={i}
          onClick={btn.onClick}
          style={{
            padding: '4px 16px',
            background: btn.active ? '#4CAF50' : '#FFC107',
            color: btn.active ? '#fff' : '#000',
            border: btn.active ? '2px solid #388E3C' : '2px solid #FF9800',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 13,
            fontWeight: 'bold',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          {btn.active ? btn.activeLabel : btn.label}
        </button>
      ))}
    </div>
  );
}
