import { useTheme } from '../hooks/useTheme';

export default function Footer() {
  const { tokens } = useTheme();
  return (
    <footer
      style={{
        marginTop: 48,
        padding: '24px 0',
        textAlign: 'center',
        fontSize: 13,
        color: tokens.muted,
        borderTop: `1px solid ${tokens.border}`,
      }}
    >
      <p style={{ margin: 0 }}>
        页面作者{' '}
        <a
          href="https://github.com/milandomio"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent }}
        >
          @milando
        </a>
        {' · '}
        感谢{' '}
        <a
          href="https://pages.cloudflare.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent }}
        >
          Cloudflare Pages
        </a>{' '}
        提供加速
      </p>
      <p style={{ margin: '4px 0 0' }}>
        社区爱好者制作，数据来源及图片版权归属于{' '}
        <a
          href="https://darkanddarker.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.accent }}
        >
          Dark and Darker
        </a>
      </p>
    </footer>
  );
}
