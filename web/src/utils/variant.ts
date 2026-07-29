export function defaultVariantSuffix(suffixes: string[]): string | undefined {
  if (suffixes.includes('5001')) return '5001';
  return suffixes[suffixes.length - 1];
}
