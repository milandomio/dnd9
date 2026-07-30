export function ssrLocalizedTitle(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  try {
    const ssr = (window as any).__SSR_DATA__;
    return ssr?.__localizedTitle;
  } catch {
    return undefined;
  }
}

export function ssrLocalizedDescription(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  try {
    const ssr = (window as any).__SSR_DATA__;
    return ssr?.__localizedDescription;
  } catch {
    return undefined;
  }
}
