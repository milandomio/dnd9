import { useTheme } from '../hooks/useTheme';

export default function Footer() {
  const { tokens } = useTheme();
  return (
    <footer
      style={{
        marginTop: 24,
        padding: '12px 0 0',
        textAlign: 'center',
        fontSize: 13,
        color: tokens.muted,
        borderTop: `1px solid ${tokens.border}`,
      }}
    >
      <p style={{ margin: 0 }}>
        © 2026{' '}
        <a
          href="https://www.bilibili.com/video/BV1hoR7BzExq"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          @milando
        </a>
        {' · '}
        <a
          href="https://discord.spellsandguns.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          Wiki社区
        </a>
        {' · '}
        <a
          href="https://chatglm.cn/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          智谱清言
        </a>
        {' · '}
        <a
          href="https://platform.deepseek.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          DeepSeek
        </a>
        {' · '}
        <a
          href="https://github.com/features/actions"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          GitHub
        </a>
        {' · '}
        <a
          href="https://pages.cloudflare.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          Cloudflare
        </a>
      </p>
      <p style={{ margin: '4px 0 0' }}>
        本应用为社区爱好者制作的非官方项目，数据来源及图片版权归属于{' '}
        <a
          href="https://darkanddarker.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent, textDecoration: 'none' }}
        >
          Dark and Darker
        </a>
      </p>
    </footer>
  );
}
