import type { DungeonModule } from '../types/data';

export function mapImageUrl(
  module: DungeonModule | undefined,
  placeholder = false
): string {
  const imageName = placeholder
    ? 'RareModule_1x1'
    : module?.img_name || module?.sl_base_name || 'RareModule_1x1';
  return `/data/img/${imageName}.webp`;
}

export function isRecognizableMapImage(url: string): boolean {
  return (
    !url.includes('/RareModule_1x1.webp') &&
    !url.includes('/UnderConstruction_1x1.webp')
  );
}
