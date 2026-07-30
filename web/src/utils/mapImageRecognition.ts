import type { CV } from '@techstark/opencv-js';

export interface MapImageTemplate {
  id: string;
  url: string;
  label: string;
  group: string;
  groupLabel: string;
}

export interface LoadedMapImageTemplate extends MapImageTemplate {
  canvas: HTMLCanvasElement;
}

export interface MapImageMatch {
  templateId: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  score: number;
  method: 'template' | 'orb';
}

export interface MapImageRecognitionOutput {
  blob: Blob;
  matches: MapImageMatch[];
  width: number;
  height: number;
  gridType: '5x5' | '7x7' | null;
}

export interface MapImageRecognitionOptions {
  threshold?: number;
}

interface OpenCvModule {
  default?: unknown;
}

interface OpenCvRuntime extends Record<string, unknown> {
  onRuntimeInitialized?: () => void;
}

interface OpenCvKeyPoint {
  pt?: { x: number; y: number };
  x?: number;
  y?: number;
}

interface OpenCvDMatch {
  distance: number;
  queryIdx: number;
  trainIdx: number;
}

interface OpenCvVector<T> {
  get(index: number): T;
  size(): number;
}

interface OrbSceneFeatures {
  mask: InstanceType<CV['Mat']>;
  keyPoints: InstanceType<CV['KeyPointVector']>;
  descriptors: InstanceType<CV['Mat']>;
  orb: InstanceType<CV['ORB']>;
}

interface WorkingMatch extends Omit<
  MapImageMatch,
  'x' | 'y' | 'width' | 'height'
> {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface SearchRegion {
  canvas: HTMLCanvasElement;
  x: number;
  y: number;
  gridHint: MapImageRecognitionOutput['gridType'];
}

const MAX_WORKING_EDGE = 600;
const TEMPLATE_SCALES = [0.32, 0.4, 0.44, 0.48, 0.6, 0.75, 1, 1.25];
const GRID_TEMPLATE_SCALES = {
  '5x5': [0.4, 0.44, 0.48],
  '7x7': [0.36, 0.4, 0.44],
} as const;
const TEMPLATE_ROTATIONS = [0, 90, 180, 270] as const;
const DEFAULT_TEMPLATE_MATCH_THRESHOLD = 0.52;
const MAX_PEAKS_PER_TEMPLATE = 8;
const MAX_SCORE_CANDIDATES = 4096;
const MAX_FINE_TEMPLATE_CANDIDATES = 18;

let openCvPromise: Promise<CV> | null = null;

function isPromiseLike(value: unknown): value is PromiseLike<unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'then' in value &&
    typeof (value as { then?: unknown }).then === 'function'
  );
}

export function loadOpenCv(): Promise<CV> {
  if (!openCvPromise) {
    openCvPromise = import('@techstark/opencv-js').then(async (module) => {
      const candidate = (module as unknown as OpenCvModule).default;
      if (!candidate) throw new Error('OpenCV.js module is empty');
      if (isPromiseLike(candidate)) return (await candidate) as CV;
      if (typeof candidate === 'object' && 'Mat' in candidate) {
        return candidate as CV;
      }
      return new Promise<CV>((resolve, reject) => {
        const runtime = candidate as OpenCvRuntime;
        const timer = window.setTimeout(
          () => reject(new Error('OpenCV.js initialization timed out')),
          30000
        );
        runtime.onRuntimeInitialized = () => {
          window.clearTimeout(timer);
          resolve(candidate as CV);
        };
      });
    });
  }
  return openCvPromise;
}

function createCanvas(width: number, height: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(width));
  canvas.height = Math.max(1, Math.round(height));
  return canvas;
}

function resizeCanvas(
  source: HTMLCanvasElement,
  scale: number
): HTMLCanvasElement {
  const canvas = createCanvas(source.width * scale, source.height * scale);
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas 2D context is unavailable');
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
  return canvas;
}

function rotateCanvas(
  source: HTMLCanvasElement,
  degrees: (typeof TEMPLATE_ROTATIONS)[number]
): HTMLCanvasElement {
  if (degrees === 0) return source;
  const swapsAxes = degrees === 90 || degrees === 270;
  const canvas = createCanvas(
    swapsAxes ? source.height : source.width,
    swapsAxes ? source.width : source.height
  );
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas 2D context is unavailable');
  context.translate(canvas.width / 2, canvas.height / 2);
  context.rotate((degrees * Math.PI) / 180);
  context.drawImage(source, -source.width / 2, -source.height / 2);
  return canvas;
}

function dominantDenseRange(
  values: Uint32Array,
  threshold: number,
  maxGap: number
): { start: number; end: number } | null {
  const ranges: Array<{ start: number; end: number }> = [];
  let start = -1;
  for (let index = 0; index <= values.length; index += 1) {
    if (index < values.length && values[index] >= threshold) {
      if (start < 0) start = index;
      continue;
    }
    if (start >= 0) {
      ranges.push({ start, end: index - 1 });
      start = -1;
    }
  }
  if (!ranges.length) return null;

  const merged: Array<{ start: number; end: number }> = [];
  for (const range of ranges) {
    const previous = merged[merged.length - 1];
    if (previous && range.start - previous.end - 1 <= maxGap) {
      previous.end = range.end;
    } else {
      merged.push({ ...range });
    }
  }
  return merged.reduce((largest, range) =>
    range.end - range.start > largest.end - largest.start ? range : largest
  );
}

function detectMapSearchRegion(source: HTMLCanvasElement): SearchRegion {
  if (source.width < 480 || source.height < 270) {
    return { canvas: source, x: 0, y: 0, gridHint: null };
  }
  const context = source.getContext('2d', { willReadFrequently: true });
  if (!context) return { canvas: source, x: 0, y: 0, gridHint: null };
  const pixels = context.getImageData(0, 0, source.width, source.height).data;
  const rowDensity = new Uint32Array(source.height);
  const columnDensity = new Uint32Array(source.width);
  for (let y = 0; y < source.height; y += 1) {
    for (let x = 0; x < source.width; x += 1) {
      const index = (y * source.width + x) * 4;
      const luminance =
        pixels[index] * 0.2126 +
        pixels[index + 1] * 0.7152 +
        pixels[index + 2] * 0.0722;
      if (luminance < 95) continue;
      rowDensity[y] += 1;
      columnDensity[x] += 1;
    }
  }
  const rows = dominantDenseRange(
    rowDensity,
    source.width * 0.15,
    Math.max(2, Math.round(source.height * 0.02))
  );
  const columns = dominantDenseRange(
    columnDensity,
    source.height * 0.3,
    Math.max(2, Math.round(source.width * 0.02))
  );
  if (!rows || !columns) return { canvas: source, x: 0, y: 0, gridHint: null };

  const padding = Math.max(
    4,
    Math.round(Math.min(source.width, source.height) * 0.02)
  );
  const left = Math.max(0, columns.start - padding);
  const top = Math.max(0, rows.start - padding);
  const right = Math.min(source.width, columns.end + padding + 1);
  const bottom = Math.min(source.height, rows.end + padding + 1);
  if (
    right - left < source.width * 0.25 ||
    bottom - top < source.height * 0.4
  ) {
    return { canvas: source, x: 0, y: 0, gridHint: null };
  }

  const canvas = createCanvas(right - left, bottom - top);
  const cropContext = canvas.getContext('2d');
  if (!cropContext) return { canvas: source, x: 0, y: 0, gridHint: null };
  cropContext.drawImage(
    source,
    left,
    top,
    canvas.width,
    canvas.height,
    0,
    0,
    canvas.width,
    canvas.height
  );
  const widthRatio = canvas.width / source.width;
  const heightRatio = canvas.height / source.height;
  const gridHint =
    widthRatio >= 0.42 && heightRatio >= 0.74
      ? '7x7'
      : widthRatio <= 0.42 && heightRatio <= 0.74
        ? '5x5'
        : null;
  return { canvas, x: left, y: top, gridHint };
}

async function blobToCanvas(blob: Blob): Promise<HTMLCanvasElement> {
  if (typeof createImageBitmap === 'function') {
    const bitmap = await createImageBitmap(blob);
    const canvas = createCanvas(bitmap.width, bitmap.height);
    const context = canvas.getContext('2d');
    if (!context) {
      bitmap.close();
      throw new Error('Canvas 2D context is unavailable');
    }
    context.drawImage(bitmap, 0, 0);
    bitmap.close();
    return canvas;
  }

  const url = URL.createObjectURL(blob);
  try {
    const image = new Image();
    image.decoding = 'async';
    image.src = url;
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error('Image decoding failed'));
    });
    const canvas = createCanvas(image.naturalWidth, image.naturalHeight);
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas 2D context is unavailable');
    context.drawImage(image, 0, 0);
    return canvas;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function loadMapImageTemplates(
  templates: MapImageTemplate[],
  onProgress?: (loaded: number, total: number) => void
): Promise<{ templates: LoadedMapImageTemplate[]; failed: number }> {
  const unique = [
    ...new Map(templates.map((template) => [template.url, template])).values(),
  ];
  let loaded = 0;
  let failed = 0;
  const results = await Promise.all(
    unique.map(async (template) => {
      try {
        const response = await fetch(template.url, { cache: 'force-cache' });
        if (!response.ok) throw new Error(`template HTTP ${response.status}`);
        const canvas = await blobToCanvas(await response.blob());
        if (canvas.width < 32 || canvas.height < 32)
          throw new Error('template is too small');
        return { ...template, canvas };
      } catch {
        failed += 1;
        return null;
      } finally {
        loaded += 1;
        onProgress?.(loaded, unique.length);
      }
    })
  );
  return {
    templates: results.filter(
      (template): template is LoadedMapImageTemplate => template !== null
    ),
    failed,
  };
}

function yieldToBrowser(): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

function intersectionOverUnion(a: WorkingMatch, b: WorkingMatch): number {
  const left = Math.max(a.x, b.x);
  const top = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  const intersection = Math.max(0, right - left) * Math.max(0, bottom - top);
  if (intersection === 0) return 0;
  return (
    intersection / (a.width * a.height + b.width * b.height - intersection)
  );
}

function mergeMatches(matches: WorkingMatch[]): WorkingMatch[] {
  const sorted = [...matches].sort((a, b) => b.score - a.score);
  const kept: WorkingMatch[] = [];
  for (const match of sorted) {
    const duplicate = kept.some(
      (existing) =>
        intersectionOverUnion(existing, match) >
        (existing.templateId === match.templateId ? 0.28 : 0.5)
    );
    if (!duplicate) kept.push(match);
  }
  return kept;
}

function inferMapGridType(
  matches: WorkingMatch[],
  searchRegion: SearchRegion
): MapImageRecognitionOutput['gridType'] {
  if (searchRegion.gridHint) return searchRegion.gridHint;
  if (searchRegion.x === 0 && searchRegion.y === 0) return null;
  const reliable = matches.filter(
    (match) => match.method === 'template' && match.score >= 0.58
  );
  const candidates = reliable.length >= 3 ? reliable : matches;
  if (candidates.length < 3) return null;
  const cellSizes = candidates
    .map((match) => Math.min(match.width, match.height))
    .filter((size) => size >= 24)
    .sort((a, b) => a - b);
  if (cellSizes.length < 3) return null;
  const medianCellSize = cellSizes[Math.floor(cellSizes.length / 2)];
  const estimatedGridSize =
    (searchRegion.canvas.width / medianCellSize +
      searchRegion.canvas.height / medianCellSize) /
    2;
  const distanceToFive = Math.abs(estimatedGridSize - 5);
  const distanceToSeven = Math.abs(estimatedGridSize - 7);
  const nearestDistance = Math.min(distanceToFive, distanceToSeven);
  if (nearestDistance > 1.25) return null;
  return distanceToFive <= distanceToSeven ? '5x5' : '7x7';
}

function collectTemplatePeaks(
  result: InstanceType<CV['Mat']>,
  templateWidth: number,
  templateHeight: number,
  template: LoadedMapImageTemplate,
  matchThreshold: number
): WorkingMatch[] {
  const candidates: Array<{ x: number; y: number; score: number }> = [];
  let bestScore = -Infinity;
  const stride = result.cols * result.rows > 900000 ? 2 : 1;
  for (let y = 0; y < result.rows; y += stride) {
    for (let x = 0; x < result.cols; x += stride) {
      const score = result.data32F[y * result.cols + x];
      if (score > bestScore) bestScore = score;
    }
  }
  if (bestScore < matchThreshold) return [];
  const threshold = Math.max(matchThreshold, bestScore - 0.08);
  for (let y = 0; y < result.rows; y += stride) {
    for (let x = 0; x < result.cols; x += stride) {
      const index = y * result.cols + x;
      const score = result.data32F[index];
      if (score < threshold) continue;
      const left = x > 0 ? result.data32F[index - 1] : -Infinity;
      const right = x + 1 < result.cols ? result.data32F[index + 1] : -Infinity;
      const top = y > 0 ? result.data32F[index - result.cols] : -Infinity;
      const bottom =
        y + 1 < result.rows ? result.data32F[index + result.cols] : -Infinity;
      if (score < left || score < right || score < top || score < bottom)
        continue;
      candidates.push({ x, y, score });
      if (candidates.length >= MAX_SCORE_CANDIDATES) break;
    }
    if (candidates.length >= MAX_SCORE_CANDIDATES) break;
  }
  candidates.sort((a, b) => b.score - a.score);
  const peaks: WorkingMatch[] = [];
  for (const candidate of candidates) {
    if (candidate.score < threshold) break;
    const match: WorkingMatch = {
      templateId: template.id,
      label: template.label,
      x: candidate.x,
      y: candidate.y,
      width: templateWidth,
      height: templateHeight,
      score: candidate.score,
      method: 'template',
    };
    if (
      !peaks.some((existing) => intersectionOverUnion(existing, match) > 0.3)
    ) {
      peaks.push(match);
    }
    if (peaks.length >= MAX_PEAKS_PER_TEMPLATE) break;
  }
  return peaks;
}

function maxMatScore(result: InstanceType<CV['Mat']>): number {
  let bestScore = -Infinity;
  for (let index = 0; index < result.data32F.length; index += 1) {
    if (result.data32F[index] > bestScore) {
      bestScore = result.data32F[index];
    }
  }
  return bestScore;
}

async function prefilterTemplates(
  cv: CV,
  scene: HTMLCanvasElement,
  templates: LoadedMapImageTemplate[],
  workingScale: number,
  templateScales: readonly number[]
): Promise<LoadedMapImageTemplate[]> {
  if (templates.length <= MAX_FINE_TEMPLATE_CANDIDATES) return templates;
  const coarseFactor = 0.5;
  const coarseScene = resizeCanvas(scene, coarseFactor);
  const sceneRgba = cv.imread(coarseScene);
  const sceneGray = new cv.Mat();
  const scores: Array<{
    template: LoadedMapImageTemplate;
    score: number;
  }> = [];
  try {
    cv.cvtColor(sceneRgba, sceneGray, cv.COLOR_RGBA2GRAY);
    for (const template of templates) {
      let bestScore = -Infinity;
      for (const rotation of TEMPLATE_ROTATIONS) {
        const rotatedTemplate = rotateCanvas(template.canvas, rotation);
        for (const relativeScale of templateScales) {
          const scaledCanvas = resizeCanvas(
            rotatedTemplate,
            workingScale * relativeScale * coarseFactor
          );
          if (
            scaledCanvas.width > sceneGray.cols ||
            scaledCanvas.height > sceneGray.rows ||
            scaledCanvas.width < 16 ||
            scaledCanvas.height < 16
          ) {
            continue;
          }
          const templateRgba = cv.imread(scaledCanvas);
          const templateGray = new cv.Mat();
          const result = new cv.Mat();
          try {
            cv.cvtColor(templateRgba, templateGray, cv.COLOR_RGBA2GRAY);
            cv.matchTemplate(
              sceneGray,
              templateGray,
              result,
              cv.TM_CCOEFF_NORMED
            );
            bestScore = Math.max(bestScore, maxMatScore(result));
          } finally {
            templateRgba.delete();
            templateGray.delete();
            result.delete();
          }
        }
      }
      scores.push({ template, score: bestScore });
      await yieldToBrowser();
    }
  } finally {
    sceneRgba.delete();
    sceneGray.delete();
  }
  return scores
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_FINE_TEMPLATE_CANDIDATES)
    .map(({ template }) => template);
}

function getKeyPointPoint(keyPoint: OpenCvKeyPoint): { x: number; y: number } {
  return keyPoint.pt ?? { x: keyPoint.x ?? 0, y: keyPoint.y ?? 0 };
}

function boxFromPoints(
  points: Array<{ x: number; y: number }>,
  maxWidth: number,
  maxHeight: number
): { x: number; y: number; width: number; height: number } | null {
  if (points.length < 4) return null;
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const x = Math.max(0, Math.min(...xs));
  const y = Math.max(0, Math.min(...ys));
  const right = Math.min(maxWidth, Math.max(...xs));
  const bottom = Math.min(maxHeight, Math.max(...ys));
  if (right - x < 24 || bottom - y < 24) return null;
  return { x, y, width: right - x, height: bottom - y };
}

function orbFallback(
  cv: CV,
  sceneGray: InstanceType<CV['Mat']>,
  template: LoadedMapImageTemplate,
  workingScale: number,
  sceneFeatures: OrbSceneFeatures
): WorkingMatch | null {
  const templateCanvas = resizeCanvas(template.canvas, workingScale);
  if (
    templateCanvas.width > sceneGray.cols ||
    templateCanvas.height > sceneGray.rows
  ) {
    return null;
  }

  const templateRgba = cv.imread(templateCanvas);
  const templateGray = new cv.Mat();
  const templateKeyPoints = new cv.KeyPointVector();
  const templateDescriptors = new cv.Mat();
  const matcher = new cv.BFMatcher(cv.NORM_HAMMING, false);
  const knnMatches = new cv.DMatchVectorVector();
  let templatePoints: InstanceType<CV['Mat']> | null = null;
  let scenePoints: InstanceType<CV['Mat']> | null = null;
  let inlierMask: InstanceType<CV['Mat']> | null = null;
  let homography: InstanceType<CV['Mat']> | null = null;
  let transformedCorners: InstanceType<CV['Mat']> | null = null;
  try {
    cv.cvtColor(templateRgba, templateGray, cv.COLOR_RGBA2GRAY);
    sceneFeatures.orb.detectAndCompute(
      templateGray,
      sceneFeatures.mask,
      templateKeyPoints,
      templateDescriptors
    );
    if (templateDescriptors.empty() || sceneFeatures.descriptors.empty())
      return null;

    matcher.knnMatch(
      templateDescriptors,
      sceneFeatures.descriptors,
      knnMatches,
      2
    );
    const goodMatches: Array<{
      templatePoint: { x: number; y: number };
      scenePoint: { x: number; y: number };
    }> = [];
    const pairs = knnMatches as unknown as OpenCvVector<
      OpenCvVector<OpenCvDMatch>
    >;
    for (let i = 0; i < pairs.size(); i += 1) {
      const pair = pairs.get(i);
      if (pair.size() < 2) continue;
      const first = pair.get(0);
      const second = pair.get(1);
      if (first.distance >= second.distance * 0.76) continue;
      const templatePoint = getKeyPointPoint(
        (templateKeyPoints as unknown as OpenCvVector<OpenCvKeyPoint>).get(
          first.queryIdx
        )
      );
      const scenePoint = getKeyPointPoint(
        (
          sceneFeatures.keyPoints as unknown as OpenCvVector<OpenCvKeyPoint>
        ).get(first.trainIdx)
      );
      goodMatches.push({ templatePoint, scenePoint });
    }
    if (goodMatches.length < 8) return null;

    const templateCoordinates = goodMatches.flatMap(({ templatePoint }) => [
      templatePoint.x,
      templatePoint.y,
    ]);
    const sceneCoordinates = goodMatches.flatMap(({ scenePoint }) => [
      scenePoint.x,
      scenePoint.y,
    ]);
    templatePoints = cv.matFromArray(
      goodMatches.length,
      1,
      cv.CV_32FC2,
      templateCoordinates
    );
    scenePoints = cv.matFromArray(
      goodMatches.length,
      1,
      cv.CV_32FC2,
      sceneCoordinates
    );
    inlierMask = new cv.Mat();
    homography = cv.findHomography(
      templatePoints,
      scenePoints,
      cv.RANSAC,
      5,
      inlierMask
    );
    if (!homography || homography.empty()) return null;

    const corners = cv.matFromArray(4, 1, cv.CV_32FC2, [
      0,
      0,
      templateCanvas.width,
      0,
      templateCanvas.width,
      templateCanvas.height,
      0,
      templateCanvas.height,
    ]);
    transformedCorners = new cv.Mat();
    cv.perspectiveTransform(corners, transformedCorners, homography);
    corners.delete();
    const points: Array<{ x: number; y: number }> = [];
    for (let i = 0; i < transformedCorners.data32F.length; i += 2) {
      points.push({
        x: transformedCorners.data32F[i],
        y: transformedCorners.data32F[i + 1],
      });
    }
    const box = boxFromPoints(points, sceneGray.cols, sceneGray.rows);
    if (!box) return null;
    const inliers = inlierMask.data8U.reduce(
      (count, value) => count + (value ? 1 : 0),
      0
    );
    if (inliers < 6) return null;
    return {
      templateId: template.id,
      label: template.label,
      ...box,
      score: Math.min(0.98, 0.58 + inliers / 45),
      method: 'orb',
    };
  } catch {
    return null;
  } finally {
    templateRgba.delete();
    templateGray.delete();
    templateKeyPoints.delete();
    templateDescriptors.delete();
    matcher.delete();
    knnMatches.delete();
    templatePoints?.delete();
    scenePoints?.delete();
    inlierMask?.delete();
    homography?.delete();
    transformedCorners?.delete();
  }
}

function createOrbSceneFeatures(
  cv: CV,
  sceneGray: InstanceType<CV['Mat']>
): OrbSceneFeatures {
  const mask = new cv.Mat();
  const keyPoints = new cv.KeyPointVector();
  const descriptors = new cv.Mat();
  const orb = new cv.ORB(1200);
  orb.detectAndCompute(sceneGray, mask, keyPoints, descriptors);
  return { mask, keyPoints, descriptors, orb };
}

function deleteOrbSceneFeatures(features: OrbSceneFeatures) {
  features.mask.delete();
  features.keyPoints.delete();
  features.descriptors.delete();
  features.orb.delete();
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('Annotated image export failed'));
    }, 'image/png');
  });
}

function drawAnnotation(
  screenshot: HTMLCanvasElement,
  matches: WorkingMatch[],
  workingScale: number
): HTMLCanvasElement {
  const output = createCanvas(screenshot.width, screenshot.height);
  const context = output.getContext('2d');
  if (!context) throw new Error('Canvas 2D context is unavailable');
  context.drawImage(screenshot, 0, 0);
  context.fillStyle = 'rgba(0, 190, 80, 0.5)';
  for (const match of matches) {
    context.fillRect(
      match.x / workingScale,
      match.y / workingScale,
      match.width / workingScale,
      match.height / workingScale
    );
  }
  return output;
}

export async function recognizeMapScreenshot(
  screenshot: HTMLCanvasElement,
  templates: LoadedMapImageTemplate[],
  cv: CV,
  options: MapImageRecognitionOptions = {}
): Promise<MapImageRecognitionOutput> {
  if (templates.length === 0) throw new Error('No map templates are available');
  const matchThreshold = Math.min(
    0.9,
    Math.max(0.2, options.threshold ?? DEFAULT_TEMPLATE_MATCH_THRESHOLD)
  );
  const workingScale = Math.min(
    1,
    MAX_WORKING_EDGE / Math.max(screenshot.width, screenshot.height)
  );
  const workingScreenshot = resizeCanvas(screenshot, workingScale);
  const searchRegion = detectMapSearchRegion(workingScreenshot);
  const templateScales = searchRegion.gridHint
    ? GRID_TEMPLATE_SCALES[searchRegion.gridHint]
    : TEMPLATE_SCALES;
  const candidateTemplates = await prefilterTemplates(
    cv,
    searchRegion.canvas,
    templates,
    workingScale,
    templateScales
  );
  const screenshotRgba = cv.imread(searchRegion.canvas);
  const screenshotGray = new cv.Mat();
  const rawMatches: WorkingMatch[] = [];
  try {
    cv.cvtColor(screenshotRgba, screenshotGray, cv.COLOR_RGBA2GRAY);
    for (const template of candidateTemplates) {
      for (const rotation of TEMPLATE_ROTATIONS) {
        const rotatedTemplate = rotateCanvas(template.canvas, rotation);
        for (const relativeScale of templateScales) {
          const scaledCanvas = resizeCanvas(
            rotatedTemplate,
            workingScale * relativeScale
          );
          if (
            scaledCanvas.width > screenshotGray.cols ||
            scaledCanvas.height > screenshotGray.rows ||
            scaledCanvas.width < 32 ||
            scaledCanvas.height < 32
          ) {
            continue;
          }
          const templateRgba = cv.imread(scaledCanvas);
          const templateGray = new cv.Mat();
          const result = new cv.Mat();
          try {
            cv.cvtColor(templateRgba, templateGray, cv.COLOR_RGBA2GRAY);
            cv.matchTemplate(
              screenshotGray,
              templateGray,
              result,
              cv.TM_CCOEFF_NORMED
            );
            rawMatches.push(
              ...collectTemplatePeaks(
                result,
                scaledCanvas.width,
                scaledCanvas.height,
                template,
                matchThreshold
              )
            );
          } finally {
            templateRgba.delete();
            templateGray.delete();
            result.delete();
          }
        }
      }
      await yieldToBrowser();
    }
    const unmatchedTemplates = candidateTemplates.filter(
      (template) =>
        !rawMatches.some((match) => match.templateId === template.id)
    );
    if (unmatchedTemplates.length > 0) {
      const sceneFeatures = createOrbSceneFeatures(cv, screenshotGray);
      try {
        for (const template of unmatchedTemplates) {
          const fallback = orbFallback(
            cv,
            screenshotGray,
            template,
            workingScale,
            sceneFeatures
          );
          if (fallback) rawMatches.push(fallback);
          await yieldToBrowser();
        }
      } finally {
        deleteOrbSceneFeatures(sceneFeatures);
      }
    }
  } finally {
    screenshotRgba.delete();
    screenshotGray.delete();
  }

  const localMatches = mergeMatches(rawMatches);
  const gridType = inferMapGridType(localMatches, searchRegion);
  const matches = localMatches.map((match) => ({
    ...match,
    x: match.x + searchRegion.x,
    y: match.y + searchRegion.y,
  }));
  const outputCanvas = drawAnnotation(screenshot, matches, workingScale);
  return {
    blob: await canvasToBlob(outputCanvas),
    matches: matches.map((match) => ({
      ...match,
      x: match.x / workingScale,
      y: match.y / workingScale,
      width: match.width / workingScale,
      height: match.height / workingScale,
    })),
    width: screenshot.width,
    height: screenshot.height,
    gridType,
  };
}

export async function decodeScreenshot(blob: Blob): Promise<HTMLCanvasElement> {
  return blobToCanvas(blob);
}
