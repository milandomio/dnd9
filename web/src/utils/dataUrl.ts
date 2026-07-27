export function dataUrl(version: string, path: string) {
  if (!version) throw new Error('Data version is not ready');
  const short = Number(version).toString(36);
  return path.replace('/data/json', `/data/${short}/json`);
}
