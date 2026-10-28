import type { DungeonModule } from '../types/data';
import { dataUrl } from './dataUrl';

export function mapImageUrl(
  module: DungeonModule | undefined,
  placeholder = false
): string {
  const imageName = placeholder
    ? 'RareModule_1x1'
    : module?.img_name || module?.sl_base_name || 'RareModule_1x1';
  return dataUrl(
    import.meta.env.VITE_DATA_VERSION || 'dev',
    `/data/img/${imageName}.webp`
  );
}

export function isRecognizableMapImage(url: string): boolean {
  return (
    !url.includes('/RareModule_1x1.webp') &&
    !url.includes('/UnderConstruction_1x1.webp')
  );
}

/**
 * 拼接模块放置限制后缀：角落优先于边缘（两者互斥）。
 * ut 为 useLocale 提供的 UI 字典查询函数。
 */
export function modulePlacementSuffix(
  module:
    | Pick<DungeonModule, 'is_edge' | 'is_corner'>
    | { is_edge?: boolean; is_corner?: boolean }
    | undefined,
  ut: (key: string) => string
): string {
  if (!module) return '';
  if (module.is_corner) return ut('ui.module.suffix.corner');
  if (module.is_edge) return ut('ui.module.suffix.edge');
  return '';
}
